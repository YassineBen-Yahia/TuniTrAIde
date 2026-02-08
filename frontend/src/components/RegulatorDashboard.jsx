import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import ApiService from '../services/api';
import {
  Shield,
  AlertTriangle,
  Eye,
  Flag,
  Search,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  X,
  FileText,
  Activity,
  Users,
  TrendingUp,
  TrendingDown,
  Clock,
  Download,
  Filter,
  Plus,
  Trash2,
  Edit3,
  CheckCircle,
  XCircle,
  Save,
  MessageSquare,
} from 'lucide-react';

const ITEMS_PER_PAGE = 8;

const RegulatorDashboard = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('transactions');
  const [transactions, setTransactions] = useState([]);
  const [suspiciousOnly, setSuspiciousOnly] = useState(false);
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTx, setSelectedTx] = useState(null);
  const [flagReason, setFlagReason] = useState('');
  const [flagging, setFlagging] = useState(false);
  const [anomalyFilter, setAnomalyFilter] = useState('');

  // Anomaly CRUD state
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(null);
  const [showValidateModal, setShowValidateModal] = useState(null);
  const [anomalyForm, setAnomalyForm] = useState({
    stock_code: '', date: '',
    volume_anomaly: 0, variation_anomaly: 0,
    variation_anomaly_post_news: 0, variation_anomaly_pre_news: 0,
    volume_anomaly_post_news: 0, volume_anomaly_pre_news: 0,
    regulator_note: '',
  });
  const [validateNote, setValidateNote] = useState('');
  const [saving, setSaving] = useState(false);

  // Pagination state
  const [txPage, setTxPage] = useState(1);
  const [anomalyPage, setAnomalyPage] = useState(1);

  // Expanded note for suspicious transactions
  const [expandedTxId, setExpandedTxId] = useState(null);

  const showSuccess = (msg) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(''), 3000);
  };

  const fetchTransactions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = suspiciousOnly
        ? await ApiService.getSuspiciousTransactions(0, 500)
        : await ApiService.getAllTransactions(0, 500);
      setTransactions(data);
    } catch (err) {
      console.error('Failed to fetch transactions:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [suspiciousOnly]);

  const fetchAnomalies = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await ApiService.getStockAnomalies(anomalyFilter || null);
      setAnomalies(data);
    } catch (err) {
      console.error('Failed to fetch anomalies:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [anomalyFilter]);

  useEffect(() => {
    if (activeTab === 'transactions') fetchTransactions();
    else fetchAnomalies();
  }, [activeTab, fetchTransactions, fetchAnomalies]);

  const handleFlag = async (txId, isSuspicious) => {
    try {
      setFlagging(true);
      await ApiService.flagTransaction(txId, isSuspicious, flagReason || null);
      setFlagReason('');
      setSelectedTx(null);
      fetchTransactions();
    } catch (err) {
      setError(err.message);
    } finally {
      setFlagging(false);
    }
  };

  // ---- Anomaly CRUD handlers ----
  const handleAddAnomaly = async () => {
    try {
      setSaving(true);
      setError(null);
      await ApiService.addAnomaly(anomalyForm);
      showSuccess('Anomaly added successfully');
      setShowAddModal(false);
      resetAnomalyForm();
      fetchAnomalies();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleEditAnomaly = async () => {
    try {
      setSaving(true);
      setError(null);
      await ApiService.editAnomaly(anomalyForm);
      showSuccess('Anomaly updated successfully');
      setShowEditModal(false);
      resetAnomalyForm();
      fetchAnomalies();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAnomaly = async (stockCode, date) => {
    try {
      setSaving(true);
      setError(null);
      await ApiService.deleteAnomaly(stockCode, date);
      showSuccess('Anomaly deleted successfully');
      setShowDeleteConfirm(null);
      fetchAnomalies();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleValidateAnomaly = async (stockCode, date, validated) => {
    try {
      setSaving(true);
      setError(null);
      await ApiService.validateAnomaly(stockCode, date, validated, validateNote);
      showSuccess(validated ? 'Anomaly validated' : 'Anomaly unvalidated');
      setShowValidateModal(null);
      setValidateNote('');
      fetchAnomalies();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const resetAnomalyForm = () => {
    setAnomalyForm({
      stock_code: '', date: '',
      volume_anomaly: 0, variation_anomaly: 0,
      variation_anomaly_post_news: 0, variation_anomaly_pre_news: 0,
      volume_anomaly_post_news: 0, volume_anomaly_pre_news: 0,
      regulator_note: '',
    });
  };

  const openEditModal = (a) => {
    setAnomalyForm({
      stock_code: a.stock_code, date: a.date,
      volume_anomaly: a.volume_anomaly, variation_anomaly: a.variation_anomaly,
      variation_anomaly_post_news: a.variation_anomaly_post_news,
      variation_anomaly_pre_news: a.variation_anomaly_pre_news,
      volume_anomaly_post_news: a.volume_anomaly_post_news,
      volume_anomaly_pre_news: a.volume_anomaly_pre_news,
      regulator_note: a.regulator_note || '',
    });
    setShowEditModal(true);
  };

  // Reset pages when filters change
  useEffect(() => { setTxPage(1); }, [searchQuery, suspiciousOnly]);
  useEffect(() => { setAnomalyPage(1); }, [anomalyFilter]);

  const filteredTransactions = transactions.filter((tx) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      tx.stock_code?.toLowerCase().includes(q) ||
      tx.stock_name?.toLowerCase().includes(q) ||
      String(tx.user_id).includes(q)
    );
  }).sort((a, b) => new Date(b.transaction_date) - new Date(a.transaction_date));

  const txTotalPages = Math.max(1, Math.ceil(filteredTransactions.length / ITEMS_PER_PAGE));
  const paginatedTransactions = filteredTransactions.slice(
    (txPage - 1) * ITEMS_PER_PAGE,
    txPage * ITEMS_PER_PAGE
  );

  const sortedAnomalies = [...anomalies].sort((a, b) => new Date(b.date) - new Date(a.date));
  const anomalyTotalPages = Math.max(1, Math.ceil(sortedAnomalies.length / ITEMS_PER_PAGE));
  const paginatedAnomalies = sortedAnomalies.slice(
    (anomalyPage - 1) * ITEMS_PER_PAGE,
    anomalyPage * ITEMS_PER_PAGE
  );

  const handleExport = () => {
    const rows = [
      ['ID', 'User', 'Stock', 'Type', 'Shares', 'Price', 'Total', 'Date', 'Suspicious', 'Reason'].join(','),
      ...filteredTransactions.map((tx) =>
        [
          tx.id,
          tx.user_id,
          tx.stock_code,
          tx.transaction_type,
          tx.shares,
          tx.price_per_share,
          tx.total_amount,
          tx.transaction_date,
          tx.is_suspicious ? 'Yes' : 'No',
          `"${(tx.suspicious_reason || '').replace(/"/g, '""')}"`,
        ].join(',')
      ),
    ].join('\n');
    const blob = new Blob([rows], { type: 'text/csv' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `regulator_transactions_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
  };

  const stats = {
    total: transactions.length,
    suspicious: transactions.filter((t) => t.is_suspicious).length,
    buys: transactions.filter((t) => t.transaction_type === 'BUY').length,
    sells: transactions.filter((t) => t.transaction_type === 'SELL').length,
  };

  if (loading && transactions.length === 0 && anomalies.length === 0) {
    return (
      <div className="min-h-screen app-shell flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto mb-4" />
          <p className="text-slate-400">Loading regulator dashboard…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen app-shell py-6">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
              <Shield className="w-7 h-7 text-amber-400" />
              Regulator Dashboard
            </h1>
            <p className="text-slate-400 mt-1">
              Monitor all market transactions and anomalies
            </p>
          </div>
          <div className="flex items-center gap-3 mt-4 md:mt-0">
            <button
              onClick={() => (activeTab === 'transactions' ? fetchTransactions() : fetchAnomalies())}
              disabled={loading}
              className="btn-secondary flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-rose-500/10 border border-rose-500/50 rounded-lg text-rose-400">
            {error}
          </div>
        )}

        {successMsg && (
          <div className="mb-6 p-4 bg-emerald-500/10 border border-emerald-500/50 rounded-lg text-emerald-400">
            {successMsg}
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { id: 'transactions', label: 'Transactions', icon: FileText },
            { id: 'anomalies', label: 'Stock Anomalies', icon: Activity },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-cyan-500 text-slate-900 shadow-lg shadow-cyan-500/25'
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* ===================== TRANSACTIONS TAB ===================== */}
        {activeTab === 'transactions' && (
          <>
            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="panel p-4 text-center">
                <div className="text-2xl font-bold text-slate-100">{stats.total}</div>
                <div className="text-xs text-slate-400 uppercase">Total Txns</div>
              </div>
              <div className="panel p-4 text-center">
                <div className="text-2xl font-bold text-rose-400">{stats.suspicious}</div>
                <div className="text-xs text-slate-400 uppercase">Suspicious</div>
              </div>
              <div className="panel p-4 text-center">
                <div className="text-2xl font-bold text-emerald-400">{stats.buys}</div>
                <div className="text-xs text-slate-400 uppercase">Buys</div>
              </div>
              <div className="panel p-4 text-center">
                <div className="text-2xl font-bold text-amber-400">{stats.sells}</div>
                <div className="text-xs text-slate-400 uppercase">Sells</div>
              </div>
            </div>

            {/* Filters */}
            <div className="panel p-4 mb-6 flex flex-col md:flex-row gap-4 items-center">
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-slate-400" />
                <button
                  onClick={() => setSuspiciousOnly(false)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    !suspiciousOnly
                      ? 'bg-cyan-500 text-slate-900'
                      : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  All
                </button>
                <button
                  onClick={() => setSuspiciousOnly(true)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    suspiciousOnly
                      ? 'bg-rose-500 text-white'
                      : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <AlertTriangle className="w-3 h-3 inline mr-1" />
                  Suspicious Only
                </button>
              </div>
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search by stock code, name, or user ID…"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="input-field pl-10 w-full"
                />
              </div>
              <button onClick={handleExport} className="btn-secondary flex items-center gap-2">
                <Download className="w-4 h-4" />
                Export
              </button>
            </div>

            {/* Transactions table */}
            <div className="panel overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="table-head">
                    <tr>
                      <th className="px-4 py-3 text-left">ID</th>
                      <th className="px-4 py-3 text-left">User</th>
                      <th className="px-4 py-3 text-left">Stock</th>
                      <th className="px-4 py-3 text-left">Type</th>
                      <th className="px-4 py-3 text-right">Shares</th>
                      <th className="px-4 py-3 text-right">Price</th>
                      <th className="px-4 py-3 text-right">Total</th>
                      <th className="px-4 py-3 text-left">Date</th>
                      <th className="px-4 py-3 text-center">Status</th>
                      <th className="px-4 py-3 text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedTransactions.length === 0 ? (
                      <tr>
                        <td colSpan={10} className="px-4 py-8 text-center text-slate-500">
                          No transactions found
                        </td>
                      </tr>
                    ) : (
                      paginatedTransactions.map((tx) => (
                        <React.Fragment key={tx.id}>
                          <tr
                            className={`table-row hover:bg-slate-800/30 ${
                              tx.is_suspicious && suspiciousOnly ? 'cursor-pointer' : ''
                            }`}
                            onClick={() => {
                              if (tx.is_suspicious && suspiciousOnly) {
                                setExpandedTxId(expandedTxId === tx.id ? null : tx.id);
                              }
                            }}
                          >
                          <td className="px-4 py-3 text-slate-400">#{tx.id}</td>
                          <td className="px-4 py-3 text-slate-300">
                            <span className="flex items-center gap-1">
                              <Users className="w-3 h-3" /> {tx.user_id}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="text-slate-100 font-medium">{tx.stock_name || tx.stock_code}</div>
                            <div className="text-xs text-slate-500">{tx.stock_code}</div>
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${
                                tx.transaction_type === 'BUY'
                                  ? 'bg-emerald-500/20 text-emerald-400'
                                  : 'bg-rose-500/20 text-rose-400'
                              }`}
                            >
                              {tx.transaction_type === 'BUY' ? (
                                <TrendingUp className="w-3 h-3" />
                              ) : (
                                <TrendingDown className="w-3 h-3" />
                              )}
                              {tx.transaction_type}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right text-slate-300">{tx.shares}</td>
                          <td className="px-4 py-3 text-right text-slate-300">
                            {tx.price_per_share?.toFixed(2)} TND
                          </td>
                          <td className="px-4 py-3 text-right text-slate-100 font-medium">
                            {tx.total_amount?.toFixed(2)} TND
                          </td>
                          <td className="px-4 py-3 text-slate-400 text-xs">
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {new Date(tx.transaction_date).toLocaleDateString()}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            {tx.is_suspicious ? (
                              <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/40">
                                <AlertTriangle className="w-3 h-3" /> Flagged
                              </span>
                            ) : (
                              <span className="text-xs text-slate-500">Clean</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <div className="flex items-center justify-center gap-1">
                              {tx.is_suspicious ? (
                                <button
                                  onClick={(e) => { e.stopPropagation(); handleFlag(tx.id, false); }}
                                  className="text-xs px-2 py-1 rounded bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors"
                                  title="Unflag transaction"
                                >
                                  Unflag
                                </button>
                              ) : (
                                <button
                                  onClick={(e) => { e.stopPropagation(); setSelectedTx(tx); }}
                                  className="text-xs px-2 py-1 rounded bg-rose-500/20 text-rose-400 hover:bg-rose-500/30 transition-colors"
                                  title="Flag as suspicious"
                                >
                                  <Flag className="w-3 h-3 inline mr-1" />
                                  Flag
                                </button>
                              )}
                              {tx.is_suspicious && suspiciousOnly && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setExpandedTxId(expandedTxId === tx.id ? null : tx.id);
                                  }}
                                  className="text-xs px-2 py-1 rounded bg-slate-700 text-slate-300 hover:bg-slate-600 transition-colors"
                                  title="View note"
                                >
                                  <MessageSquare className="w-3 h-3 inline mr-1" />
                                  Note
                                </button>
                              )}
                            </div>
                          </td>
                          </tr>
                          {/* Expanded note row for suspicious transactions */}
                          {tx.is_suspicious && expandedTxId === tx.id && (
                            <tr className="bg-rose-500/5 border-t border-rose-500/20">
                              <td colSpan={10} className="px-6 py-4">
                                <div className="flex items-start gap-3">
                                  <MessageSquare className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
                                  <div>
                                    <div className="text-xs font-medium text-rose-400 uppercase tracking-wider mb-1">
                                      Suspicious Reason / Note
                                    </div>
                                    <p className="text-sm text-slate-300">
                                      {tx.suspicious_reason || tx.notes || 'No reason provided.'}
                                    </p>
                                    {tx.flagged_at && (
                                      <p className="text-xs text-slate-500 mt-2">
                                        Flagged on {new Date(tx.flagged_at).toLocaleString()}
                                        {tx.flagged_by_regulator_id ? ` by Regulator #${tx.flagged_by_regulator_id}` : ''}
                                      </p>
                                    )}
                                  </div>
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Transactions Pagination */}
            {filteredTransactions.length > ITEMS_PER_PAGE && (
              <Pagination
                currentPage={txPage}
                totalPages={txTotalPages}
                onPageChange={setTxPage}
                totalItems={filteredTransactions.length}
              />
            )}

            {/* Flag modal */}
            {selectedTx && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 backdrop-blur-sm">
                <div className="panel p-6 w-full max-w-md">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                      <Flag className="w-5 h-5 text-rose-400" />
                      Flag Transaction #{selectedTx.id}
                    </h3>
                    <button onClick={() => setSelectedTx(null)} className="text-slate-400 hover:text-slate-200">
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                  <p className="text-sm text-slate-400 mb-4">
                    {selectedTx.stock_name || selectedTx.stock_code} — {selectedTx.transaction_type}{' '}
                    {selectedTx.shares} shares @ {selectedTx.price_per_share?.toFixed(2)} TND
                  </p>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Reason for flagging
                  </label>
                  <textarea
                    rows={3}
                    value={flagReason}
                    onChange={(e) => setFlagReason(e.target.value)}
                    placeholder="Describe why this transaction is suspicious…"
                    className="input-field w-full mb-4"
                  />
                  <div className="flex justify-end gap-3">
                    <button onClick={() => setSelectedTx(null)} className="btn-secondary">
                      Cancel
                    </button>
                    <button
                      onClick={() => handleFlag(selectedTx.id, true)}
                      disabled={flagging}
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-500 text-white font-medium hover:bg-rose-400 transition-colors disabled:opacity-50"
                    >
                      {flagging ? 'Flagging…' : 'Confirm Flag'}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {/* ===================== ANOMALIES TAB ===================== */}
        {activeTab === 'anomalies' && (
          <>
            <div className="panel p-4 mb-6 flex flex-col md:flex-row gap-4 items-center">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Filter by stock code…"
                  value={anomalyFilter}
                  onChange={(e) => setAnomalyFilter(e.target.value)}
                  className="input-field pl-10 w-full"
                />
              </div>
              <button onClick={fetchAnomalies} className="btn-secondary flex items-center gap-2">
                <Search className="w-4 h-4" />
                Search
              </button>
              <button
                onClick={() => { resetAnomalyForm(); setShowAddModal(true); }}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-500 text-slate-900 font-medium hover:bg-cyan-400 transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add Anomaly
              </button>
            </div>

            {/* Anomaly stats */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
              <div className="panel p-4 text-center">
                <div className="text-2xl font-bold text-slate-100">{anomalies.length}</div>
                <div className="text-xs text-slate-400 uppercase">Total Anomalies</div>
              </div>
              <div className="panel p-4 text-center">
                <div className="text-2xl font-bold text-emerald-400">{anomalies.filter(a => a.validated).length}</div>
                <div className="text-xs text-slate-400 uppercase">Validated</div>
              </div>
              <div className="panel p-4 text-center">
                <div className="text-2xl font-bold text-amber-400">{anomalies.filter(a => !a.validated).length}</div>
                <div className="text-xs text-slate-400 uppercase">Pending</div>
              </div>
            </div>

            <div className="panel overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="table-head">
                    <tr>
                      <th className="px-4 py-3 text-left">Stock</th>
                      <th className="px-4 py-3 text-left">Date</th>
                      <th className="px-4 py-3 text-center">Volume</th>
                      <th className="px-4 py-3 text-center">Variation</th>
                      <th className="px-4 py-3 text-center">Var Post</th>
                      <th className="px-4 py-3 text-center">Var Pre</th>
                      <th className="px-4 py-3 text-center">Vol Post</th>
                      <th className="px-4 py-3 text-center">Vol Pre</th>
                      <th className="px-4 py-3 text-center">Status</th>
                      <th className="px-4 py-3 text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedAnomalies.length === 0 ? (
                      <tr>
                        <td colSpan={10} className="px-4 py-8 text-center text-slate-500">
                          No anomalies found
                        </td>
                      </tr>
                    ) : (
                      paginatedAnomalies.map((a, i) => (
                        <tr key={i} className="table-row hover:bg-slate-800/30">
                          <td className="px-4 py-3">
                            <div className="text-slate-100 font-medium">{a.stock_name}</div>
                            <div className="text-xs text-slate-500">{a.stock_code}</div>
                          </td>
                          <td className="px-4 py-3 text-slate-400">{a.date}</td>
                          <td className="px-4 py-3 text-center">
                            <AnomalyBadge value={a.volume_anomaly} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <AnomalyBadge value={a.variation_anomaly} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <AnomalyBadge value={a.variation_anomaly_post_news} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <AnomalyBadge value={a.variation_anomaly_pre_news} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <AnomalyBadge value={a.volume_anomaly_post_news} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <AnomalyBadge value={a.volume_anomaly_pre_news} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            {a.validated ? (
                              <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                                <CheckCircle className="w-3 h-3" /> Validated
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/40">
                                <Clock className="w-3 h-3" /> Pending
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <div className="flex items-center justify-center gap-1">
                              {!a.validated ? (
                                <button
                                  onClick={() => { setShowValidateModal(a); setValidateNote(''); }}
                                  className="text-xs px-2 py-1 rounded bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors"
                                  title="Validate anomaly"
                                >
                                  <CheckCircle className="w-3 h-3 inline mr-0.5" />
                                  Validate
                                </button>
                              ) : (
                                <button
                                  onClick={() => handleValidateAnomaly(a.stock_code, a.date, false)}
                                  className="text-xs px-2 py-1 rounded bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 transition-colors"
                                  title="Unvalidate anomaly"
                                >
                                  <XCircle className="w-3 h-3 inline mr-0.5" />
                                  Undo
                                </button>
                              )}
                              <button
                                onClick={() => openEditModal(a)}
                                className="text-xs px-2 py-1 rounded bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 transition-colors"
                                title="Edit anomaly"
                              >
                                <Edit3 className="w-3 h-3" />
                              </button>
                              <button
                                onClick={() => setShowDeleteConfirm(a)}
                                className="text-xs px-2 py-1 rounded bg-rose-500/20 text-rose-400 hover:bg-rose-500/30 transition-colors"
                                title="Delete anomaly"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Anomalies Pagination */}
            {sortedAnomalies.length > ITEMS_PER_PAGE && (
              <Pagination
                currentPage={anomalyPage}
                totalPages={anomalyTotalPages}
                onPageChange={setAnomalyPage}
                totalItems={sortedAnomalies.length}
              />
            )}

            {/* ===== ADD ANOMALY MODAL ===== */}
            {showAddModal && (
              <AnomalyFormModal
                title="Add Anomaly"
                form={anomalyForm}
                setForm={setAnomalyForm}
                onSave={handleAddAnomaly}
                onClose={() => setShowAddModal(false)}
                saving={saving}
                editableCode
              />
            )}

            {/* ===== EDIT ANOMALY MODAL ===== */}
            {showEditModal && (
              <AnomalyFormModal
                title={`Edit Anomaly — ${anomalyForm.stock_code} (${anomalyForm.date})`}
                form={anomalyForm}
                setForm={setAnomalyForm}
                onSave={handleEditAnomaly}
                onClose={() => setShowEditModal(false)}
                saving={saving}
              />
            )}

            {/* ===== DELETE CONFIRM MODAL ===== */}
            {showDeleteConfirm && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 backdrop-blur-sm">
                <div className="panel p-6 w-full max-w-md">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                      <Trash2 className="w-5 h-5 text-rose-400" />
                      Delete Anomaly
                    </h3>
                    <button onClick={() => setShowDeleteConfirm(null)} className="text-slate-400 hover:text-slate-200">
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                  <p className="text-sm text-slate-400 mb-4">
                    Are you sure you want to clear all anomaly flags for{' '}
                    <span className="text-slate-200 font-medium">{showDeleteConfirm.stock_name}</span> on{' '}
                    <span className="text-slate-200 font-medium">{showDeleteConfirm.date}</span>? This will
                    set all anomaly columns to 0 in the CSV.
                  </p>
                  <div className="flex justify-end gap-3">
                    <button onClick={() => setShowDeleteConfirm(null)} className="btn-secondary">
                      Cancel
                    </button>
                    <button
                      onClick={() => handleDeleteAnomaly(showDeleteConfirm.stock_code, showDeleteConfirm.date)}
                      disabled={saving}
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-500 text-white font-medium hover:bg-rose-400 transition-colors disabled:opacity-50"
                    >
                      {saving ? 'Deleting…' : 'Confirm Delete'}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* ===== VALIDATE MODAL ===== */}
            {showValidateModal && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 backdrop-blur-sm">
                <div className="panel p-6 w-full max-w-md">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-emerald-400" />
                      Validate Anomaly
                    </h3>
                    <button onClick={() => setShowValidateModal(null)} className="text-slate-400 hover:text-slate-200">
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                  <p className="text-sm text-slate-400 mb-4">
                    Validate anomaly for{' '}
                    <span className="text-slate-200 font-medium">{showValidateModal.stock_name}</span> on{' '}
                    <span className="text-slate-200 font-medium">{showValidateModal.date}</span>.
                  </p>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Regulator Note (optional)</label>
                  <textarea
                    rows={3}
                    value={validateNote}
                    onChange={(e) => setValidateNote(e.target.value)}
                    placeholder="Add a note about this anomaly…"
                    className="input-field w-full mb-4"
                  />
                  <div className="flex justify-end gap-3">
                    <button onClick={() => setShowValidateModal(null)} className="btn-secondary">
                      Cancel
                    </button>
                    <button
                      onClick={() => handleValidateAnomaly(showValidateModal.stock_code, showValidateModal.date, true)}
                      disabled={saving}
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500 text-white font-medium hover:bg-emerald-400 transition-colors disabled:opacity-50"
                    >
                      {saving ? 'Validating…' : 'Confirm Validate'}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

/** Google-style numbered pagination */
const Pagination = ({ currentPage, totalPages, onPageChange, totalItems }) => {
  // Build page numbers to display (show max 7 page buttons)
  const getPageNumbers = () => {
    const pages = [];
    const maxVisible = 7;

    if (totalPages <= maxVisible) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      // Always show first page
      pages.push(1);

      let start = Math.max(2, currentPage - 2);
      let end = Math.min(totalPages - 1, currentPage + 2);

      // Shift window so we always show 5 middle pages
      if (currentPage <= 3) {
        end = Math.min(totalPages - 1, maxVisible - 1);
      }
      if (currentPage >= totalPages - 2) {
        start = Math.max(2, totalPages - maxVisible + 2);
      }

      if (start > 2) pages.push('...');
      for (let i = start; i <= end; i++) pages.push(i);
      if (end < totalPages - 1) pages.push('...');

      // Always show last page
      pages.push(totalPages);
    }
    return pages;
  };

  const startItem = (currentPage - 1) * ITEMS_PER_PAGE + 1;
  const endItem = Math.min(currentPage * ITEMS_PER_PAGE, totalItems);

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 mt-4 px-2">
      <span className="text-xs text-slate-500">
        Showing {startItem}–{endItem} of {totalItems}
      </span>

      <div className="flex items-center gap-1">
        {/* Previous */}
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        {/* Page numbers */}
        {getPageNumbers().map((page, idx) =>
          page === '...' ? (
            <span key={`ellipsis-${idx}`} className="px-2 text-slate-600 text-sm select-none">…</span>
          ) : (
            <button
              key={page}
              onClick={() => onPageChange(page)}
              className={`min-w-[32px] h-8 rounded-lg text-sm font-medium transition-colors ${
                page === currentPage
                  ? 'bg-cyan-500 text-slate-900 shadow-lg shadow-cyan-500/25'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
              }`}
            >
              {page}
            </button>
          )
        )}

        {/* Next */}
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

const AnomalyBadge = ({ value }) => {
  if (value === 1) {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-400">
        <AlertTriangle className="w-3 h-3" /> Yes
      </span>
    );
  }
  return <span className="text-xs text-slate-600">—</span>;
};

/** Reusable form modal for Add / Edit anomaly */
const AnomalyFormModal = ({ title, form, setForm, onSave, onClose, saving, editableCode = false }) => {
  const anomalyFields = [
    { key: 'volume_anomaly', label: 'Volume Anomaly' },
    { key: 'variation_anomaly', label: 'Variation Anomaly' },
    { key: 'variation_anomaly_post_news', label: 'Variation Post-News' },
    { key: 'variation_anomaly_pre_news', label: 'Variation Pre-News' },
    { key: 'volume_anomaly_post_news', label: 'Volume Post-News' },
    { key: 'volume_anomaly_pre_news', label: 'Volume Pre-News' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 backdrop-blur-sm">
      <div className="panel p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
            {editableCode ? <Plus className="w-5 h-5 text-cyan-400" /> : <Edit3 className="w-5 h-5 text-cyan-400" />}
            {title}
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Stock code & date */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Stock Code</label>
              <input
                type="text"
                value={form.stock_code}
                onChange={(e) => setForm({ ...form, stock_code: e.target.value })}
                placeholder="e.g. TN0001100254"
                className="input-field w-full"
                disabled={!editableCode}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Date</label>
              <input
                type="date"
                value={form.date}
                onChange={(e) => setForm({ ...form, date: e.target.value })}
                className="input-field w-full"
                disabled={!editableCode}
              />
            </div>
          </div>

          {/* Anomaly toggles */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Anomaly Flags</label>
            <div className="grid grid-cols-2 gap-3">
              {anomalyFields.map(({ key, label }) => (
                <label
                  key={key}
                  className={`flex items-center gap-2 p-3 rounded-lg cursor-pointer transition-colors border ${
                    form[key] === 1
                      ? 'bg-rose-500/10 border-rose-500/40 text-rose-400'
                      : 'bg-slate-800/50 border-slate-700 text-slate-400'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={form[key] === 1}
                    onChange={(e) => setForm({ ...form, [key]: e.target.checked ? 1 : 0 })}
                    className="rounded border-slate-600 text-rose-500 focus:ring-rose-500"
                  />
                  <span className="text-sm">{label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Note */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Regulator Note</label>
            <textarea
              rows={2}
              value={form.regulator_note}
              onChange={(e) => setForm({ ...form, regulator_note: e.target.value })}
              placeholder="Optional note…"
              className="input-field w-full"
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button
            onClick={onSave}
            disabled={saving || !form.stock_code || !form.date}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-500 text-slate-900 font-medium hover:bg-cyan-400 transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default RegulatorDashboard;
