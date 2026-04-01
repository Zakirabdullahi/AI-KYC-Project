import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
    fetchAdminStats, fetchAllUsers, fetchUserDetails, fetchUserKycDocs,
    adminAdjustBalance, fetchPendingVerifications, decideVerification,
    fetchAllTransactions, adminResetPassword, deleteUserKycDocs, logout
} from '../api';
import {
    ShieldCheck, LogOut, CheckCircle, XCircle, Users, Activity,
    BarChart2, DollarSign, Eye, Search, RefreshCw, ImageIcon, Key, Trash2
} from 'lucide-react';

const fmtMoney = (n) => `KSh ${Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;

const statusColor = {
    verified: { bg: '#2f855a', text: 'white' },
    pending: { bg: '#b7791f', text: 'white' },
    suspended: { bg: '#e53e3e', text: 'white' },
    rejected: { bg: '#9b2c2c', text: 'white' },
    unverified: { bg: '#4a5568', text: 'white' },
};

// ─── User Details Modal ───────────────────────────────────────────────────────
function UserModal({ user, onClose, onDecision }) {
    const [kycDocs, setKycDocs] = useState(null);
    const [showDocs, setShowDocs] = useState(false);
    const [resettingPwd, setResettingPwd] = useState(false);
    const [newPwd, setNewPwd] = useState('');
    const [pwdBusy, setPwdBusy] = useState(false);
    const [zoomedImage, setZoomedImage] = useState(null);
    const [deleteBusy, setDeleteBusy] = useState(false);

    const loadDocs = async () => {
        try {
            const res = await fetchUserKycDocs(user.id);
            setKycDocs(res.data);
            setShowDocs(true);
        } catch { toast.error('Failed to load KYC documents.'); }
    };

    const sc = statusColor[user.verification_status] || { bg: '#4a5568', text: 'white' };

    return (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: 20 }} onClick={onClose}>
            <div style={{ background: '#1a202c', borderRadius: 12, padding: 32, maxWidth: 640, width: '100%', border: '1px solid #4a5568', position: 'relative', maxHeight: '90vh', overflowY: 'auto' }} onClick={e => e.stopPropagation()}>
                <button onClick={onClose} style={{ position: 'absolute', top: 16, right: 16, background: 'transparent', color: '#a0aec0' }}><XCircle size={24} /></button>

                <h2 style={{ color: 'white', fontSize: 22, marginBottom: 4 }}>{user.full_name}</h2>
                <p style={{ color: '#a0aec0', marginBottom: 20 }}>{user.email}</p>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
                    {[['Role', user.role?.toUpperCase()], ['Status', ''], ['Phone', user.phone || '—'], ['Address', user.address || '—'], ['Member Since', user.created_at ? new Date(user.created_at).toLocaleDateString() : '—'], ['Accounts', user.accounts?.length]].map(([label, val], i) => (
                        <div key={label} style={{ background: '#2d3748', padding: 12, borderRadius: 8 }}>
                            <p style={{ color: '#a0aec0', fontSize: 12, marginBottom: 4 }}>{label}</p>
                            {label === 'Status' ? <span style={{ fontSize: 12, padding: '3px 8px', borderRadius: 4, background: sc.bg, color: sc.text }}>{user.verification_status?.toUpperCase()}</span> : <p style={{ color: 'white', fontWeight: 500, wordBreak: 'break-all' }}>{val}</p>}
                        </div>
                    ))}
                </div>

                <h3 style={{ color: 'white', marginBottom: 12 }}>Accounts</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
                    {user.accounts?.length === 0 && <p style={{ color: '#a0aec0', fontSize: 13 }}>No accounts.</p>}
                    {user.accounts?.map(acc => (
                        <div key={acc.id} style={{ display: 'flex', justifyContent: 'space-between', padding: 12, background: '#2d3748', borderRadius: 8 }}>
                            <span style={{ color: 'white', fontWeight: 500 }}>{acc.account_type.toUpperCase()} (••{acc.account_number.slice(-4)})</span>
                            <span style={{ color: '#00a9e0', fontWeight: 700 }}>{fmtMoney(acc.balance)}</span>
                        </div>
                    ))}
                </div>

                {user.loans?.length > 0 && (<>
                    <h3 style={{ color: 'white', marginBottom: 12 }}>Active Loans</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
                        {user.loans.map(l => (
                            <div key={l.id} style={{ display: 'flex', justifyContent: 'space-between', padding: 12, background: '#2d3748', borderRadius: 8 }}>
                                <span style={{ color: '#a0aec0', fontSize: 13 }}>Loan #{l.id} — {l.status}</span>
                                <span style={{ color: '#fc8181' }}>{fmtMoney(l.balance_remaining)} remaining</span>
                            </div>
                        ))}
                    </div>
                </>)}

                <h3 style={{ color: 'white', marginBottom: 12 }}>Recent Transactions</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 20, maxHeight: 200, overflowY: 'auto' }}>
                    {user.recent_transactions?.length === 0 && <p style={{ color: '#a0aec0', fontSize: 13 }}>No transactions.</p>}
                    {user.recent_transactions?.map(t => (
                        <div key={t.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: '#2d3748', borderRadius: 6 }}>
                            <span style={{ color: '#a0aec0', fontSize: 12 }}>{t.type.toUpperCase()} — {(t.description || '').split('|')[0]}</span>
                            <span style={{ color: '#00a9e0', fontSize: 12, fontWeight: 600 }}>{fmtMoney(t.amount)}</span>
                        </div>
                    ))}
                </div>

                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
                    <button onClick={loadDocs} style={{ background: '#4a5568', color: 'white', padding: '8px 14px', borderRadius: 6, display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}><ImageIcon size={14} /> View KYC Docs</button>
                    {user.verification_status !== 'suspended' ? (
                        <button onClick={() => { if (window.confirm('Suspend this user?')) onDecision(user.id, 'suspended'); }} style={{ background: '#e53e3e', color: 'white', padding: '8px 14px', borderRadius: 6, fontWeight: 600, fontSize: 13 }}>Suspend</button>
                    ) : (
                        <button onClick={() => { if (window.confirm('Restore access?')) onDecision(user.id, 'verified'); }} style={{ background: '#2f855a', color: 'white', padding: '8px 14px', borderRadius: 6, fontWeight: 600, fontSize: 13 }}>Restore Access</button>
                    )}
                    {user.verification_status === 'pending' && <>
                        <button onClick={() => onDecision(user.id, 'verified')} style={{ background: '#2f855a', color: 'white', padding: '8px 14px', borderRadius: 6, fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}><CheckCircle size={14} /> Approve</button>
                        <button onClick={() => onDecision(user.id, 'rejected')} style={{ background: '#9b2c2c', color: 'white', padding: '8px 14px', borderRadius: 6, fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}><XCircle size={14} /> Reject</button>
                    </>}
                    <button onClick={() => setResettingPwd(!resettingPwd)} style={{ background: '#2c5282', color: 'white', padding: '8px 14px', borderRadius: 6, fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}><Key size={14} /> Reset Password</button>
                </div>
            </div>

            {resettingPwd && (
                <div style={{ background: '#2d3748', padding: 16, borderRadius: 8, marginBottom: 16, border: '1px solid #4a5568' }}>
                    <h4 style={{ color: 'white', marginBottom: 12, fontSize: 14 }}>Reset User Password</h4>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <input
                            type="text"
                            placeholder="Enter new password (min 6 chars)"
                            value={newPwd}
                            onChange={e => setNewPwd(e.target.value)}
                            style={{ flex: 1, background: '#1a202c', border: '1px solid #4a5568', padding: '8px 12px', borderRadius: 6, color: 'white', fontSize: 13 }}
                        />
                        <button
                            disabled={pwdBusy || newPwd.length < 6}
                            onClick={async () => {
                                setPwdBusy(true);
                                try {
                                    const res = await adminResetPassword(user.id, newPwd);
                                    toast.success(res.data.message);
                                    setResettingPwd(false);
                                    setNewPwd('');
                                } catch (e) {
                                    toast.error(e.response?.data?.detail || 'Reset failed');
                                } finally {
                                    setPwdBusy(false);
                                }
                            }}
                            style={{ background: '#e53e3e', color: 'white', padding: '8px 16px', borderRadius: 6, fontSize: 13, fontWeight: 600, opacity: (pwdBusy || newPwd.length < 6) ? 0.5 : 1 }}
                        >
                            {pwdBusy ? 'Saving...' : 'Confirm Reset'}
                        </button>
                    </div>
                </div>
            )}

            {showDocs && kycDocs && (
                <div style={{ borderTop: '1px solid #4a5568', paddingTop: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                        <h3 style={{ color: 'white', margin: 0 }}>KYC Documents</h3>
                        {kycDocs.has_docs && (
                            <button
                                disabled={deleteBusy}
                                onClick={async () => {
                                    if (window.confirm('Are you absolutely sure you want to permanently delete these documents? This action cannot be undone.')) {
                                        setDeleteBusy(true);
                                        try {
                                            const res = await deleteUserKycDocs(user.id);
                                            toast.success(res.data.message);
                                            setKycDocs({ ...kycDocs, has_docs: false, front_doc: null, back_doc: null, selfie: null });
                                        } catch (e) {
                                            toast.error('Failed to delete docs');
                                        } finally {
                                            setDeleteBusy(false);
                                        }
                                    }
                                }}
                                style={{ background: '#e53e3e', color: 'white', padding: '6px 12px', borderRadius: 6, fontSize: 12, display: 'flex', alignItems: 'center', gap: 4, fontWeight: 600, opacity: deleteBusy ? 0.5 : 1 }}
                            >
                                <Trash2 size={13} /> Delete Documents
                            </button>
                        )}
                    </div>
                    {!kycDocs.has_docs && <p style={{ color: '#a0aec0', fontSize: 13 }}>No documents submitted yet.</p>}
                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                        {[['Front ID', kycDocs.front_doc], ['Back ID', kycDocs.back_doc], ['Selfie', kycDocs.selfie]].map(([label, src]) => src && (
                            <div key={label} style={{ flex: '1 1 160px' }}>
                                <p style={{ color: '#a0aec0', fontSize: 11, marginBottom: 6 }}>{label}</p>
                                <img
                                    src={src.startsWith('data:') ? src : `data:image/jpeg;base64,${src}`}
                                    alt={label}
                                    onClick={(e) => { e.stopPropagation(); setZoomedImage(src.startsWith('data:') ? src : `data:image/jpeg;base64,${src}`); }}
                                    style={{ width: '100%', borderRadius: 8, border: '1px solid #4a5568', cursor: 'zoom-in' }}
                                />
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {zoomedImage && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.9)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: 20 }} onClick={() => setZoomedImage(null)}>
                    <button onClick={() => setZoomedImage(null)} style={{ position: 'absolute', top: 20, right: 20, background: 'rgba(255,255,255,0.2)', color: 'white', borderRadius: '50%', width: 44, height: 44, display: 'flex', alignItems: 'center', justifyContent: 'center', border: 'none', cursor: 'pointer' }}><XCircle size={28} /></button>
                    <img src={zoomedImage} alt="Zoomed Document" style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', borderRadius: 8 }} onClick={e => e.stopPropagation()} />
                </div>
            )}
        </div>
    );
}

// ─── Overview Tab ─────────────────────────────────────────────────────────────
function OverviewTab({ stats }) {
    if (!stats) return <div style={{ color: '#a0aec0' }}>Loading stats...</div>;
    const { users, transactions, finances } = stats;
    return (
        <div>
            <h2 style={{ color: 'white', marginBottom: 24 }}>System Overview</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 16, marginBottom: 24 }}>
                {[
                    { label: 'Total Customers', value: users.total, color: '#00a9e0', sub: `${users.verified} verified` },
                    { label: 'Pending KYC', value: users.pending, color: '#f6ad55', sub: 'awaiting review' },
                    { label: 'Unverified', value: users.unverified, color: '#a0aec0', sub: 'no KYC submitted' },
                    { label: 'Suspended', value: users.suspended, color: '#fc8181', sub: 'access blocked' },
                    { label: 'Transactions', value: transactions.total, color: '#68d391', sub: `${transactions.deposits} deposits` },
                ].map(c => (
                    <div key={c.label} style={{ background: '#2d3748', borderRadius: 10, padding: 20, borderTop: `3px solid ${c.color}` }}>
                        <p style={{ color: '#a0aec0', fontSize: 12, marginBottom: 8 }}>{c.label}</p>
                        <div style={{ fontSize: 24, fontWeight: 700, color: c.color }}>{c.value}</div>
                        <div style={{ fontSize: 11, color: '#718096', marginTop: 4 }}>{c.sub}</div>
                    </div>
                ))}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div style={{ background: '#2d3748', borderRadius: 10, padding: 20 }}>
                    <h3 style={{ color: 'white', marginBottom: 16 }}>Transaction Breakdown</h3>
                    {[['Deposits', transactions.deposits, '#68d391'], ['Withdrawals', transactions.withdrawals, '#fc8181'], ['Transfers', transactions.transfers, '#00a9e0']].map(([label, val, color]) => (
                        <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid #4a5568' }}>
                            <span style={{ color: '#a0aec0' }}>{label}</span>
                            <span style={{ color, fontWeight: 600 }}>{val}</span>
                        </div>
                    ))}
                </div>
                <div style={{ background: '#2d3748', borderRadius: 10, padding: 20 }}>
                    <h3 style={{ color: 'white', marginBottom: 16 }}>Financial Summary</h3>
                    {[['Assets Under Management', fmtMoney(finances.total_assets_under_management), '#68d391'], ['Outstanding Loans', fmtMoney(finances.total_outstanding_loans), '#fc8181']].map(([label, val, color]) => (
                        <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid #4a5568' }}>
                            <span style={{ color: '#a0aec0' }}>{label}</span>
                            <span style={{ color, fontWeight: 600 }}>{val}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

// ─── Verification Queue Tab ───────────────────────────────────────────────────
function VerificationTab({ pending, onDecision, onViewUser }) {
    return (
        <div>
            <h2 style={{ color: 'white', marginBottom: 24 }}>Verification Queue ({pending.length})</h2>
            {pending.length === 0 ? <div style={{ background: '#2d3748', borderRadius: 10, padding: 40, textAlign: 'center', color: '#a0aec0' }}>No pending verifications. All caught up! ✓</div> : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {pending.map(p => (
                        <div key={p.id} style={{ background: '#2d3748', border: '1px solid #4a5568', padding: 16, borderRadius: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                                <div style={{ fontWeight: 600, color: 'white' }}>{p.full_name}</div>
                                <div style={{ fontSize: 12, color: '#a0aec0', marginTop: 2 }}>{p.email}</div>
                            </div>
                            <div style={{ display: 'flex', gap: 8 }}>
                                <button onClick={() => onViewUser(p.id)} style={{ background: '#4a5568', color: 'white', padding: '6px 12px', borderRadius: 4, fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}><Eye size={12} /> Review</button>
                                <button onClick={() => onDecision(p.id, 'verified')} style={{ background: '#2f855a', color: 'white', padding: '6px 12px', borderRadius: 4, display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}><CheckCircle size={12} /> Approve</button>
                                <button onClick={() => onDecision(p.id, 'rejected')} style={{ background: '#9b2c2c', color: 'white', padding: '6px 12px', borderRadius: 4, display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}><XCircle size={12} /> Reject</button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

// ─── Users Tab ────────────────────────────────────────────────────────────────
function UsersTab({ users, onViewUser, onRefresh }) {
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const filtered = users.filter(u => {
        const matchSearch = !search || u.full_name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase());
        const matchStatus = !statusFilter || u.verification_status === statusFilter;
        return matchSearch && matchStatus;
    });
    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                <h2 style={{ color: 'white' }}>All Users ({filtered.length})</h2>
                <button onClick={onRefresh} style={{ background: '#4a5568', color: 'white', padding: '6px 12px', borderRadius: 6, display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}><RefreshCw size={14} /> Refresh</button>
            </div>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
                <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
                    <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#718096' }} />
                    <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search name or email..." style={{ width: '100%', background: '#2d3748', border: '1px solid #4a5568', borderRadius: 6, padding: '8px 8px 8px 34px', color: 'white', fontSize: 13 }} />
                </div>
                <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} style={{ background: '#2d3748', border: '1px solid #4a5568', borderRadius: 6, padding: '8px 12px', color: 'white', fontSize: 13 }}>
                    <option value="">All Statuses</option>
                    {['pending', 'verified', 'rejected', 'suspended', 'unverified'].map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
                </select>
            </div>
            <div style={{ background: '#2d3748', borderRadius: 10, overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead><tr style={{ borderBottom: '1px solid #4a5568' }}>{['Name', 'Email', 'Role', 'Status', 'Joined', 'Actions'].map(h => <th key={h} style={{ padding: '12px 16px', textAlign: 'left', color: '#a0aec0', fontSize: 12, fontWeight: 600, textTransform: 'uppercase' }}>{h}</th>)}</tr></thead>
                    <tbody>
                        {filtered.length === 0 && <tr><td colSpan="6" style={{ padding: 30, textAlign: 'center', color: '#a0aec0' }}>No users found.</td></tr>}
                        {filtered.map(u => {
                            const sc = statusColor[u.verification_status] || { bg: '#4a5568', text: 'white' };
                            return (
                                <tr key={u.id} style={{ borderBottom: '1px solid #4a5568' }}>
                                    <td style={{ padding: '12px 16px', color: 'white', fontWeight: 500 }}>{u.full_name}</td>
                                    <td style={{ padding: '12px 16px', color: '#a0aec0', fontSize: 13 }}>{u.email}</td>
                                    <td style={{ padding: '12px 16px' }}><span style={{ background: u.role === 'admin' ? '#4a5568' : '#2c5282', color: 'white', padding: '2px 8px', borderRadius: 12, fontSize: 11 }}>{u.role.toUpperCase()}</span></td>
                                    <td style={{ padding: '12px 16px' }}><span style={{ background: sc.bg, color: sc.text, padding: '3px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600 }}>{u.verification_status.toUpperCase()}</span></td>
                                    <td style={{ padding: '12px 16px', color: '#a0aec0', fontSize: 12 }}>{u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}</td>
                                    <td style={{ padding: '12px 16px' }}><button onClick={() => onViewUser(u.id)} style={{ background: '#4a5568', color: 'white', padding: '4px 10px', borderRadius: 4, fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}><Eye size={12} /> View</button></td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

// ─── Transactions Monitor Tab ─────────────────────────────────────────────────
function TransactionsMonitorTab({ transactions }) {
    const [filter, setFilter] = useState('');
    const visible = filter ? transactions.filter(t => t.type === filter) : transactions;
    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                <h2 style={{ color: 'white' }}>Global Transaction Monitor</h2>
                <div style={{ display: 'flex', gap: 8 }}>
                    {['', 'deposit', 'withdrawal', 'transfer'].map(t => (
                        <button key={t} onClick={() => setFilter(t)} style={{ background: filter === t ? '#00a9e0' : '#4a5568', color: 'white', padding: '5px 12px', borderRadius: 4, fontSize: 12 }}>
                            {t ? t.charAt(0).toUpperCase() + t.slice(1) : 'All'}
                        </button>
                    ))}
                </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: '60vh', overflowY: 'auto' }}>
                {visible.length === 0 && <div style={{ background: '#2d3748', borderRadius: 8, padding: 30, textAlign: 'center', color: '#a0aec0' }}>No transactions found.</div>}
                {visible.map(tx => {
                    const typeColor = { deposit: '#68d391', withdrawal: '#fc8181', transfer: '#00a9e0' }[tx.type] || '#a0aec0';
                    return (
                        <div key={tx.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px', background: '#2d3748', borderRadius: 6, borderLeft: `4px solid ${typeColor}` }}>
                            <div>
                                <div style={{ color: 'white', fontWeight: 500, fontSize: 13 }}>{tx.type.toUpperCase()}: {(tx.description || 'System Transaction').split('|')[0]}</div>
                                <div style={{ color: '#a0aec0', fontSize: 11, marginTop: 2 }}>TX #{tx.id} | Accts: {tx.from_account_id || '—'} → {tx.to_account_id || '—'} | {new Date(tx.timestamp).toLocaleString()}</div>
                            </div>
                            <div style={{ color: typeColor, fontWeight: 700, alignSelf: 'center' }}>{fmtMoney(tx.amount)}</div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

// ─── Balance Adjustment Tab ───────────────────────────────────────────────────
function BalanceAdjustTab({ users }) {
    const [form, setForm] = useState({ user_id: '', operation: 'credit', amount: '', account_type: 'checking', reason: '' });
    const [busy, setBusy] = useState(false);

    const submit = async (e) => {
        e.preventDefault();
        if (!form.user_id || !form.amount) return toast.error('Fill all required fields.');
        setBusy(true);
        try {
            const res = await adminAdjustBalance(form.user_id, { operation: form.operation, amount: parseFloat(form.amount), account_type: form.account_type, reason: form.reason || 'Admin adjustment' });
            toast.success(res.data.message);
            setForm(f => ({ ...f, amount: '', reason: '' }));
        } catch (e) { toast.error(e.response?.data?.detail || 'Adjustment failed.'); }
        finally { setBusy(false); }
    };

    return (
        <div>
            <h2 style={{ color: 'white', marginBottom: 8 }}>Balance Adjustment</h2>
            <p style={{ color: '#a0aec0', fontSize: 13, marginBottom: 24 }}>Manually credit or debit any user account. All adjustments are logged and the user is notified.</p>
            <div style={{ background: '#2d3748', borderRadius: 12, padding: 28, maxWidth: 500 }}>
                <form onSubmit={submit}>
                    <div style={{ marginBottom: 16 }}>
                        <label style={{ display: 'block', color: '#a0aec0', fontSize: 12, marginBottom: 6 }}>Select User</label>
                        <select style={{ width: '100%', background: '#1a202c', border: '1px solid #4a5568', borderRadius: 6, padding: '8px 12px', color: 'white' }} value={form.user_id} onChange={e => setForm(f => ({ ...f, user_id: e.target.value }))}>
                            <option value="">— Select user —</option>
                            {users.filter(u => u.role !== 'admin').map(u => <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>)}
                        </select>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                        <div>
                            <label style={{ display: 'block', color: '#a0aec0', fontSize: 12, marginBottom: 6 }}>Operation</label>
                            <select style={{ width: '100%', background: '#1a202c', border: '1px solid #4a5568', borderRadius: 6, padding: '8px 12px', color: 'white' }} value={form.operation} onChange={e => setForm(f => ({ ...f, operation: e.target.value }))}>
                                <option value="credit">Credit (Add)</option>
                                <option value="debit">Debit (Remove)</option>
                            </select>
                        </div>
                        <div>
                            <label style={{ display: 'block', color: '#a0aec0', fontSize: 12, marginBottom: 6 }}>Account Type</label>
                            <select style={{ width: '100%', background: '#1a202c', border: '1px solid #4a5568', borderRadius: 6, padding: '8px 12px', color: 'white' }} value={form.account_type} onChange={e => setForm(f => ({ ...f, account_type: e.target.value }))}>
                                <option value="checking">Checking</option>
                                <option value="savings">Savings</option>
                            </select>
                        </div>
                    </div>
                    <div style={{ marginBottom: 16 }}>
                        <label style={{ display: 'block', color: '#a0aec0', fontSize: 12, marginBottom: 6 }}>Amount (KSh)</label>
                        <input type="number" min="0.01" step="0.01" placeholder="0.00" style={{ width: '100%', background: '#1a202c', border: '1px solid #4a5568', borderRadius: 6, padding: '8px 12px', color: 'white' }} value={form.amount} onChange={e => setForm(f => ({ ...f, amount: e.target.value }))} />
                    </div>
                    <div style={{ marginBottom: 20 }}>
                        <label style={{ display: 'block', color: '#a0aec0', fontSize: 12, marginBottom: 6 }}>Reason / Note</label>
                        <input placeholder="e.g. Goodwill credit, Error correction" style={{ width: '100%', background: '#1a202c', border: '1px solid #4a5568', borderRadius: 6, padding: '8px 12px', color: 'white' }} value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))} />
                    </div>
                    <button type="submit" disabled={busy} style={{ width: '100%', background: form.operation === 'credit' ? '#2f855a' : '#e53e3e', color: 'white', padding: '10px 0', borderRadius: 6, fontWeight: 600, fontSize: 14 }}>
                        <DollarSign size={16} style={{ display: 'inline', marginRight: 6 }} />
                        {busy ? 'Processing...' : `${form.operation === 'credit' ? 'Credit' : 'Debit'} Account`}
                    </button>
                </form>
            </div>
        </div>
    );
}

// ─── Root Admin Panel ─────────────────────────────────────────────────────────
export default function AdminPanel() {
    const navigate = useNavigate();
    const [stats, setStats] = useState(null);
    const [users, setUsers] = useState([]);
    const [pending, setPending] = useState([]);
    const [transactions, setTransactions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('Overview');
    const [selectedUser, setSelectedUser] = useState(null);

    const loadAll = useCallback(async () => {
        try {
            const [statsRes, uRes, pRes, tRes] = await Promise.all([
                fetchAdminStats(), fetchAllUsers(), fetchPendingVerifications(), fetchAllTransactions()
            ]);
            setStats(statsRes.data);
            setUsers(uRes.data);
            setPending(pRes.data);
            setTransactions(tRes.data);
        } catch { toast.error('Admin session expired'); navigate('/login'); }
        finally { setLoading(false); }
    }, [navigate]);

    useEffect(() => { loadAll(); }, [loadAll]);

    const handleDecision = async (userId, decision) => {
        try {
            await decideVerification(userId, decision);
            toast.success(`User ${decision} successfully.`);
            if (selectedUser?.id === userId) {
                const res = await fetchUserDetails(userId);
                setSelectedUser(res.data);
            }
            loadAll();
        } catch { toast.error('Failed to update status.'); }
    };

    const handleViewUser = async (userId) => {
        try {
            const res = await fetchUserDetails(userId);
            setSelectedUser(res.data);
        } catch { toast.error('Failed to load user details.'); }
    };

    const handleLogout = () => { logout(); navigate('/login'); };

    if (loading) return <div style={{ padding: 50, textAlign: 'center', color: '#00a9e0', fontWeight: 600 }}>Loading Secure Admin Environment...</div>;

    const navTabs = [
        { label: 'Overview', icon: <BarChart2 size={16} /> },
        { label: 'Verification', icon: <ShieldCheck size={16} />, badge: pending.length },
        { label: 'Users', icon: <Users size={16} /> },
        { label: 'Transactions', icon: <Activity size={16} /> },
        { label: 'Balance Adjust', icon: <DollarSign size={16} /> },
    ];

    const renderTab = () => {
        switch (activeTab) {
            case 'Overview': return <OverviewTab stats={stats} />;
            case 'Verification': return <VerificationTab pending={pending} onDecision={handleDecision} onViewUser={handleViewUser} />;
            case 'Users': return <UsersTab users={users} onViewUser={handleViewUser} onRefresh={loadAll} />;
            case 'Transactions': return <TransactionsMonitorTab transactions={transactions} />;
            case 'Balance Adjust': return <BalanceAdjustTab users={users} />;
            default: return null;
        }
    };

    return (
        <div style={{ display: 'flex', minHeight: '100vh', background: '#1a202c' }}>
            {/* Admin Sidebar */}
            <aside style={{ width: 220, background: '#000', borderRight: '1px solid #2d3748', padding: '28px 16px', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
                <div style={{ color: '#00a9e0', fontSize: 18, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 32 }}>
                    <ShieldCheck size={20} /> ADMIN
                </div>
                <nav style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1 }}>
                    {navTabs.map(tab => (
                        <button key={tab.label} onClick={() => setActiveTab(tab.label)} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderRadius: 8, background: activeTab === tab.label ? '#2d3748' : 'transparent', color: activeTab === tab.label ? 'white' : '#a0aec0', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: activeTab === tab.label ? 600 : 400, textAlign: 'left', position: 'relative', transition: 'all 0.2s' }}>
                            {tab.icon} {tab.label}
                            {tab.badge > 0 && <span style={{ position: 'absolute', right: 10, background: '#e53e3e', color: 'white', borderRadius: '50%', width: 18, height: 18, fontSize: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{tab.badge}</span>}
                        </button>
                    ))}
                </nav>
                <button onClick={handleLogout} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', color: '#fc8181', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: 13 }}>
                    <LogOut size={16} /> Secure Exit
                </button>
            </aside>

            {/* Main Content */}
            <main style={{ flex: 1, padding: 40, color: '#f7fafc', overflowY: 'auto' }}>
                {renderTab()}
            </main>

            {selectedUser && <UserModal user={selectedUser} onClose={() => setSelectedUser(null)} onDecision={handleDecision} />}
        </div>
    );
}
