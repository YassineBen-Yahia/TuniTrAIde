# train_rl.py
import os
import sys
from pathlib import Path
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback
from rl_env import MultiCodeTunisEnv
import glob

CSV_PATH = "../data/historical_data.csv"
MODEL_DIR = "models"
MODEL_PATH = f"{MODEL_DIR}/ppo_all_codes.zip"
CHECKPOINT_DIR = f"{MODEL_DIR}/checkpoints"

TOTAL_TIMESTEPS = 400_000
N_ENVS = 4


class NaNDetectionCallback(BaseCallback):
    """Detects NaN values in training and saves checkpoint before crash"""
    
    def __init__(self, check_freq: int = 1000):
        super().__init__()
        self.check_freq = check_freq
        self.last_save_step = 0
    
    def _on_step(self) -> bool:
        if self.num_timesteps % self.check_freq == 0:
            try:
                # Check policy parameters for NaN
                for param in self.model.policy.parameters():
                    if np.isnan(param.data.cpu().numpy()).any():
                        print(f"\n⚠️  NaN detected in policy at step {self.num_timesteps}!")
                        self._save_emergency()
                        return False
                
                # Check value estimates
                if hasattr(self.model, 'value_function'):
                    test_obs = self.training_env.reset()
                    if test_obs is not None:
                        with np.errstate(all='ignore'):
                            values = self.model.value_function(test_obs)
                            if np.isnan(values).any():
                                print(f"\n⚠️  NaN in value function at step {self.num_timesteps}!")
                                self._save_emergency()
                                return False
                
            except Exception as e:
                print(f"\n❌ Error during NaN check: {e}")
        
        return True
    
    def _save_emergency(self):
        """Save emergency checkpoint"""
        os.makedirs(CHECKPOINT_DIR, exist_ok=True)
        checkpoint_path = f"{CHECKPOINT_DIR}/emergency_checkpoint_{self.num_timesteps}.zip"
        self.model.save(checkpoint_path)
        print(f"💾 Emergency checkpoint saved: {checkpoint_path}")


class StableCallback(BaseCallback):
    """Monitor training stability and adjust if needed"""
    
    def __init__(self, check_freq: int = 5000):
        super().__init__()
        self.check_freq = check_freq
        self.unstable_count = 0
    
    def _on_step(self) -> bool:
        if self.num_timesteps % self.check_freq == 0:
            if self.logger.name_to_value and 'rollout/ep_rew_mean' in self.logger.name_to_value:
                ep_rew_mean = self.logger.name_to_value.get('rollout/ep_rew_mean', 0)
                if ep_rew_mean != ep_rew_mean or abs(ep_rew_mean) > 10:  # NaN or exploding
                    self.unstable_count += 1
                    print(f"⚠️  Unstable reward detected: {ep_rew_mean}")
                else:
                    self.unstable_count = max(0, self.unstable_count - 1)
        
        return True


def make_env():
    return MultiCodeTunisEnv(
        csv_path=CSV_PATH,
        episode_len=200,
        top_n_codes=50,
        min_rows_per_code=120,
        drawdown_lambda=0.02,
        buy_frac=0.25,
        sell_frac=0.25,
    )


def find_latest_checkpoint():
    """Find the most recent checkpoint to resume from"""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    checkpoints = glob.glob(f"{CHECKPOINT_DIR}/rl_model_*.zip")
    if checkpoints:
        latest = max(checkpoints, key=os.path.getctime)
        return latest
    return None

import torch as th

def resume_or_create_model(env):
    """Resume from latest checkpoint or create new model"""
    latest = find_latest_checkpoint()

    if latest:
        print(f"\n📂 Resuming from checkpoint: {latest}")
        try:
            model = PPO.load(latest, env=env, device="cpu")
            print(f"✅ Successfully loaded model from {latest}")
            return model
        except Exception as e:
            print(f"❌ Failed to load checkpoint: {e}")
            print("Creating fresh model...")

    # ✅ Create new model (stable)
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        n_steps=256,                 # per env
        batch_size=512,
        learning_rate=2e-4,
        gamma=0.99,
        gae_lambda=0.95,
        ent_coef=0.01,
        vf_coef=0.5,
        max_grad_norm=0.5,
        clip_range=0.2,
        use_sde=False,
        policy_kwargs=dict(
            net_arch=dict(pi=[256, 256], vf=[256, 256]),
            activation_fn=th.nn.Tanh,   # ✅ FIX
        ),
        tensorboard_log="./tb_logs",
    )

    print("✅ Created fresh PPO model")
    return model



def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    
    print("🚀 Starting RL Training...")
    print(f"CSV Path: {CSV_PATH}")
    print(f"Model Dir: {MODEL_DIR}")
    print(f"Checkpoints: {CHECKPOINT_DIR}")
    
    try:
        # Create environment
        env = SubprocVecEnv([make_env for _ in range(N_ENVS)])
        
        # Create or resume model
        model = resume_or_create_model(env)
        
        # Setup callbacks
        checkpoint_callback = CheckpointCallback(
            save_freq=10_000,
            save_path=CHECKPOINT_DIR,
            name_prefix="rl_model",
            save_replay_buffer=False,
        )
        
        nan_callback = NaNDetectionCallback(check_freq=1000)
        stable_callback = StableCallback(check_freq=5000)
        
        print(f"\n📊 Training for {TOTAL_TIMESTEPS:,} timesteps")
        print(f"   Environs: {N_ENVS}")
        print(f"   Check NaN every: 1000 steps")
        print(f"   Save checkpoint every: 10000 steps\n")
        
        # Train
        model.learn(
            total_timesteps=TOTAL_TIMESTEPS,
            progress_bar=True,
            callback=[checkpoint_callback, nan_callback, stable_callback],
            tb_log_name="ppo_training"
        )
        
        # Save final model
        model.save(MODEL_PATH)
        print(f"\n✅ Training complete! Final model saved: {MODEL_PATH}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Training interrupted by user")
        print("Last checkpoint saved automatically")
        if env is not None:
            env.close()
        sys.exit(0)
        
    except ValueError as e:
        if "invalid values" in str(e) or "nan" in str(e).lower():
            print(f"\n❌ NaN/Invalid values detected: {e}")
            print("Saved emergency checkpoint. Try resuming training.")
            env.close()
            sys.exit(1)
        else:
            raise
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        print("\nLast checkpoint (if any) saved. Try resuming training.")
        env.close()
        sys.exit(1)
        
    finally:
        env.close()


if __name__ == "__main__":
    main()

