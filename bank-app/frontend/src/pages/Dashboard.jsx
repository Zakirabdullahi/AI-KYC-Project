import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
    fetchMe, fetchAccounts, fetchTransactions, submitVerification,
    executeTransfer, addFunds, withdrawFunds, logout,
    fetchLoans, applyLoan, repayLoan,
    fetchStatement, downloadStatementPDF, fetchNotifications, markNotificationRead, markAllNotificationsRead,
    updateProfile, changePassword
} from '../api';
import {
    LayoutDashboard, CreditCard, ArrowRightLeft, History, Landmark,
    TrendingUp, FileText, Bell, Settings, LogOut,
    AlertTriangle, CheckCircle2, Shield, Smartphone, Lock, RefreshCcw,
    ArrowUpRight, ArrowDownRight, Plus, Download, ChevronRight,
    Minus, Send, DollarSign, Calendar, User, Key, BookOpen, Eye, EyeOff,
    Menu, X
} from 'lucide-react';
import KycPopup from '../components/KycPopup';
import { BarChart, Bar, XAxis, YAxis, Tooltip, PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

const COLORS = ['#00a9e0', '#004c97', '#009688', '#e53e3e'];
const fmtMoney = (n) => `KSh ${Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;

// ─── Action Modal ─────────────────────────────────────────────────────────────
function ActionModal({ title, onClose, children }) {
    return (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
            <div className="card" style={{ width: '440px', maxWidth: '95vw', position: 'relative' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                    <h3 style={{ margin: 0 }}>{title}</h3>
                    <button onClick={onClose} className="btn-icon-minimal">✕</button>
                </div>
                {children}
            </div>
        </div>
    );
}

// ─── Dashboard Tab ────────────────────────────────────────────────────────────
function DashboardTab({ user, accounts, transactions, showBalance }) {
    const now = new Date();
    const accountIds = accounts.map(a => a.id);
    const totalBalance = accounts.reduce((s, a) => s + a.balance, 0);
    const currentMonthTx = transactions.filter(tx => {
        const d = new Date(tx.timestamp);
        return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
    });
    let monthlySpending = 0, incomeThisMonth = 0;
    currentMonthTx.forEach(tx => {
        if (accountIds.includes(tx.to_account_id)) incomeThisMonth += tx.amount;
        else monthlySpending += tx.amount;
    });
    const spendingData = [
        { name: 'Jan', amount: Math.max(0, monthlySpending - 500) },
        { name: 'Feb', amount: Math.max(0, monthlySpending - 200) },
        { name: 'Mar', amount: Math.max(0, monthlySpending + 100) },
        { name: now.toLocaleString('default', { month: 'short' }), amount: monthlySpending || 850 },
    ];
    const categoryData = [
        { name: 'Transfers', value: monthlySpending * 0.4 || 400 },
        { name: 'Withdrawals', value: monthlySpending * 0.6 || 600 },
        { name: 'Fees', value: 15 },
    ];
    return (
        <>
            <div className="grid-4">
                <div className="summary-card"><h2>Total Balance <Landmark size={16} /></h2><div className="value">{showBalance ? fmtMoney(totalBalance) : '****'}</div><div className="subtext trend-up"><ArrowUpRight size={14} /> +2.4% from last month</div></div>
                <div className="summary-card"><h2>Monthly Spending <TrendingUp size={16} /></h2><div className="value">{showBalance ? fmtMoney(monthlySpending) : '****'}</div><div className="subtext trend-down"><ArrowDownRight size={14} /> -1.2% vs average</div></div>
                <div className="summary-card"><h2>Income This Month <ArrowRightLeft size={16} /></h2><div className="value">{showBalance ? fmtMoney(incomeThisMonth) : '****'}</div><div className="subtext trend-up"><ArrowUpRight size={14} /> +5.0% from last month</div></div>
                <div className="summary-card"><h2>Credit Score <Shield size={16} /></h2><div className="value" style={{ color: 'var(--success)' }}>750</div><div className="subtext">Excellent Tier</div></div>
            </div>
            <div className="grid-2">
                <div className="card"><h3 style={{ marginBottom: 20, fontSize: 16 }}>Monthly Spending</h3><div style={{ height: 200 }}><ResponsiveContainer><BarChart data={spendingData} margin={{ left: -20 }}><XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#718096' }} /><YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#718096' }} /><Tooltip /><Bar dataKey="amount" fill="var(--bank-accent)" radius={[4, 4, 0, 0]} barSize={32} /></BarChart></ResponsiveContainer></div></div>
                <div className="card"><h3 style={{ marginBottom: 20, fontSize: 16 }}>Spending Categories</h3><div style={{ height: 200 }}><ResponsiveContainer><PieChart><Pie data={categoryData} cx="50%" cy="50%" innerRadius={55} outerRadius={75} paddingAngle={2} dataKey="value">{categoryData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div></div>
            </div>
            <div className="tx-table-container">
                <div className="tx-table-header"><h2>Recent Transactions</h2></div>
                <table className="tx-table"><thead><tr><th>Description</th><th>Date</th><th>Status</th><th style={{ textAlign: 'right' }}>Amount</th></tr></thead>
                    <tbody>{transactions.length === 0 ? (<tr><td colSpan="4" style={{ textAlign: 'center', padding: 30, color: '#718096' }}>No transactions yet.</td></tr>) : transactions.slice(0, 8).map(tx => {
                        const isCredit = accountIds.includes(tx.to_account_id);
                        return (<tr key={tx.id}><td><div className="tx-desc-cell"><div className={`tx-icon-wrapper ${tx.type === 'deposit' ? 'tx-icon-deposit' : tx.type === 'withdrawal' ? 'tx-icon-withdrawal' : 'tx-icon-transfer'}`}>{tx.type === 'deposit' ? <Plus size={14} /> : <Minus size={14} />}</div><div><div style={{ fontWeight: 600 }}>{tx.type.charAt(0).toUpperCase() + tx.type.slice(1)}</div><div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{(tx.description || '').split('|')[0]}</div></div></div></td><td style={{ fontSize: 13 }}>{new Date(tx.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</td><td><span className="tx-status-badge completed">Completed</span></td><td style={{ textAlign: 'right' }} className={isCredit ? 'tx-amount-positive' : 'tx-amount-negative'}>{isCredit ? '+' : '-'}{fmtMoney(tx.amount)}</td></tr>);
                    })}</tbody>
                </table>
            </div>
        </>
    );
}

// ─── Accounts Tab ─────────────────────────────────────────────────────────────
function AccountsTab({ accounts, onRefresh, showBalance }) {
    const [modal, setModal] = useState(null); // { type:'deposit'|'withdraw', accountId }
    const [amount, setAmount] = useState('');
    const [depositMethod, setDepositMethod] = useState('mpesa'); // mpesa | card
    const [phone, setPhone] = useState('');
    const [cardDetails, setCardDetails] = useState({ number: '', expiry: '', cvv: '' });
    const [busy, setBusy] = useState(false);

    const submit = async () => {
        const amt = parseFloat(amount);
        if (!amt || amt <= 0) {
            alert("Wait! You need to enter a valid amount to deposit first.");
            return toast.error('Enter a valid amount.');
        }
        
        if (modal.type === 'deposit') {
            if (depositMethod === 'mpesa' && (!phone || phone.length < 9)) {
                alert("Wait! You must enter a valid M-PESA phone number (e.g. 0712345678) before clicking deposit.");
                return toast.error('Enter a valid M-PESA phone number.');
            }
            if (depositMethod === 'card' && (!cardDetails.number || cardDetails.number.length < 15)) {
                alert("Wait! You must enter a valid card number.");
                return toast.error('Enter a valid card number.');
            }
        }

        setBusy(true);
        try {
            if (modal.type === 'deposit') { 
                const payload = { 
                    amount: amt, 
                    account_id: modal.accountId,
                    payment_method: depositMethod,
                    phone: depositMethod === 'mpesa' ? phone : undefined
                };
                if (depositMethod === 'mpesa') toast.success(`M-PESA STK Push initiated for ${phone}...`);
                if (depositMethod === 'card') toast.success(`Processing card payment...`);
                
                await addFunds(payload); 
                toast.success(`Deposit of ${fmtMoney(amt)} successful.`); 
            } else { 
                const payload = { amount: amt, account_id: modal.accountId };
                await withdrawFunds(payload); 
                toast.success(`Withdrew ${fmtMoney(amt)}`); 
            }
            setModal(null); setAmount(''); setPhone(''); setCardDetails({ number: '', expiry: '', cvv: '' });
            onRefresh();
        } catch (e) { toast.error(e.response?.data?.detail || 'Operation failed.'); }
        finally { setBusy(false); }
    };

    return (
        <div>
            <h2 style={{ marginBottom: 24 }}>My Accounts</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                {accounts.map(acc => (
                    <div key={acc.id} className={`account-card ${acc.account_type === 'savings' ? 'account-savings' : 'account-checking'}`} style={{ padding: 28 }}>
                        <div className="account-header">
                            <div><div className="account-type">Premium {acc.account_type.charAt(0).toUpperCase() + acc.account_type.slice(1)}</div><div className="account-number">• • • • {acc.account_number.slice(-4)}</div></div>
                            <div className="account-badge">Active</div>
                        </div>
                        <div className="account-balance-label">Available Balance</div>
                        <div className="account-balance">{showBalance ? fmtMoney(acc.balance) : '****'}</div>
                        <div className="account-actions">
                            <button className="account-btn" onClick={() => { setModal({ type: 'deposit', accountId: acc.id }); setAmount(''); }}><Plus size={14} /> Deposit</button>
                            <button className="account-btn" onClick={() => { setModal({ type: 'withdraw', accountId: acc.id }); setAmount(''); }}><Minus size={14} /> Withdraw</button>
                        </div>
                    </div>
                ))}
            </div>
            {modal && (
                <ActionModal title={modal.type === 'deposit' ? 'Deposit Funds' : 'Withdraw Funds'} onClose={() => setModal(null)}>
                    {modal.type === 'deposit' && (
                        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
                            <button onClick={() => setDepositMethod('mpesa')} className={depositMethod === 'mpesa' ? 'btn-primary' : 'btn-secondary'} style={{ flex: 1, padding: '8px', fontSize: 13, background: depositMethod === 'mpesa' ? '#2f855a' : undefined, borderColor: depositMethod === 'mpesa' ? '#2f855a' : undefined }}>M-PESA</button>
                            <button onClick={() => setDepositMethod('card')} className={depositMethod === 'card' ? 'btn-primary' : 'btn-secondary'} style={{ flex: 1, padding: '8px', fontSize: 13 }}>Debit/Credit Card</button>
                        </div>
                    )}

                    <label style={{ display: 'block', marginBottom: 8, color: 'var(--text-muted)', fontSize: 13 }}>Amount (KSh)</label>
                    <input className="form-input" type="number" min="1" placeholder="0.00" value={amount} onChange={e => setAmount(e.target.value)} style={{ width: '100%', marginBottom: 20 }} />
                    
                    {modal.type === 'deposit' && depositMethod === 'mpesa' && (
                        <div style={{ marginBottom: 20 }}>
                            <label style={{ display: 'block', marginBottom: 8, color: 'var(--text-muted)', fontSize: 13 }}>M-PESA Phone Number</label>
                            <input className="form-input" type="text" placeholder="e.g. 0712345678" value={phone} onChange={e => setPhone(e.target.value)} style={{ width: '100%' }} />
                            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>You will receive an STK Push prompt on this number.</p>
                        </div>
                    )}

                    {modal.type === 'deposit' && depositMethod === 'card' && (
                        <div style={{ marginBottom: 20 }}>
                            <label style={{ display: 'block', marginBottom: 8, color: 'var(--text-muted)', fontSize: 13 }}>Card Details</label>
                            <input className="form-input" type="text" placeholder="0000 0000 0000 0000" value={cardDetails.number} onChange={e => setCardDetails(f => ({ ...f, number: e.target.value }))} style={{ width: '100%', marginBottom: 12 }} />
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                                <input className="form-input" type="text" placeholder="MM/YY" value={cardDetails.expiry} onChange={e => setCardDetails(f => ({ ...f, expiry: e.target.value }))} style={{ width: '100%' }} />
                                <input className="form-input" type="text" placeholder="CVV" value={cardDetails.cvv} onChange={e => setCardDetails(f => ({ ...f, cvv: e.target.value }))} style={{ width: '100%' }} />
                            </div>
                        </div>
                    )}

                    <button className="btn-primary" style={{ width: '100%', background: modal.type === 'deposit' && depositMethod === 'mpesa' ? '#2f855a' : undefined }} onClick={submit} disabled={busy}>
                        {busy ? 'Processing...' : modal.type === 'deposit' ? `Confirm Deposit (${depositMethod.toUpperCase()})` : 'Confirm Withdrawal'}
                    </button>
                </ActionModal>
            )}
        </div>
    );
}

// ─── Transfers Tab ────────────────────────────────────────────────────────────
function TransfersTab({ user, accounts, onRefresh, showBalance }) {
    const [form, setForm] = useState({ to_account_number: '', amount: '', description: '' });
    const [busy, setBusy] = useState(false);
    const isVerified = user?.verification_status === 'verified';

    const submit = async (e) => {
        e.preventDefault();
        if (!form.to_account_number || !form.amount) return toast.error('Fill all required fields.');
        setBusy(true);
        try {
            await executeTransfer({ to_account_number: form.to_account_number, amount: parseFloat(form.amount), description: form.description });
            toast.success('Transfer successful!');
            setForm({ to_account_number: '', amount: '', description: '' });
            onRefresh();
        } catch (e) { toast.error(e.response?.data?.detail || 'Transfer failed.'); }
        finally { setBusy(false); }
    };

    return (
        <div>
            <h2 style={{ marginBottom: 24 }}>Send Money</h2>
            {!isVerified && <div className="verification-banner" style={{ marginBottom: 24 }}><div className="banner-content"><div className="banner-icon"><AlertTriangle size={20} /></div><div className="banner-text"><h3>Verification Required</h3><p>Complete KYC to unlock transfers.</p></div></div></div>}
            <div className="card" style={{ maxWidth: 540 }}>
                <form onSubmit={submit}>
                    <div style={{ marginBottom: 20 }}>
                        <label className="form-label">From Account</label>
                        <select className="form-input" style={{ width: '100%' }}>
                            {accounts.map(a => <option key={a.id} value={a.id}>{a.account_type.toUpperCase()} — {showBalance ? fmtMoney(a.balance) : '****'}</option>)}
                        </select>
                    </div>
                    <div style={{ marginBottom: 20 }}>
                        <label className="form-label">Recipient Account Number <span style={{ color: 'var(--danger)' }}>*</span></label>
                        <input className="form-input" style={{ width: '100%' }} placeholder="Enter 10-digit account number" value={form.to_account_number} onChange={e => setForm(f => ({ ...f, to_account_number: e.target.value }))} disabled={!isVerified} />
                    </div>
                    <div style={{ marginBottom: 20 }}>
                        <label className="form-label">Amount (KSh) <span style={{ color: 'var(--danger)' }}>*</span></label>
                        <input className="form-input" style={{ width: '100%' }} type="number" min="1" placeholder="0.00" value={form.amount} onChange={e => setForm(f => ({ ...f, amount: e.target.value }))} disabled={!isVerified} />
                    </div>
                    <div style={{ marginBottom: 24 }}>
                        <label className="form-label">Description (optional)</label>
                        <input className="form-input" style={{ width: '100%' }} placeholder="e.g. Rent payment" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} disabled={!isVerified} />
                    </div>
                    <button type="submit" className="btn-primary" style={{ width: '100%' }} disabled={busy || !isVerified}>
                        <Send size={16} /> {busy ? 'Processing...' : 'Send Transfer'}
                    </button>
                </form>
            </div>
        </div>
    );
}

// ─── Transactions Tab ─────────────────────────────────────────────────────────
function TransactionsTab({ transactions, accounts }) {
    const [filter, setFilter] = useState('all');
    const [page, setPage] = useState(0);
    const PER_PAGE = 15;
    const accountIds = accounts.map(a => a.id);
    const filtered = filter === 'all' ? transactions : transactions.filter(t => t.type === filter);
    const pages = Math.ceil(filtered.length / PER_PAGE);
    const visible = filtered.slice(page * PER_PAGE, page * PER_PAGE + PER_PAGE);

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                <h2>Transaction History</h2>
                <div style={{ display: 'flex', gap: 8 }}>
                    {['all', 'deposit', 'withdrawal', 'transfer'].map(t => (
                        <button key={t} onClick={() => { setFilter(t); setPage(0); }} className={filter === t ? 'btn-primary' : 'btn-secondary'} style={{ padding: '6px 14px', fontSize: 13 }}>
                            {t.charAt(0).toUpperCase() + t.slice(1)}
                        </button>
                    ))}
                </div>
            </div>
            <div className="tx-table-container">
                <table className="tx-table">
                    <thead><tr><th>Description</th><th>Type</th><th>Date & Time</th><th>Status</th><th style={{ textAlign: 'right' }}>Amount</th></tr></thead>
                    <tbody>{visible.length === 0 ? (<tr><td colSpan="5" style={{ textAlign: 'center', padding: 30, color: '#718096' }}>No transactions found.</td></tr>) : visible.map(tx => {
                        const isCredit = accountIds.includes(tx.to_account_id);
                        const d = new Date(tx.timestamp);
                        return (<tr key={tx.id}>
                            <td><div style={{ fontWeight: 500 }}>{(tx.description || '').split('|')[0]}</div><div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Ref: {(tx.description || '').split('Ref: ')[1] || '—'}</div></td>
                            <td><span className={`tx-status-badge ${tx.type}`} style={{ background: tx.type === 'deposit' ? '#f0fff4' : tx.type === 'withdrawal' ? '#fff5f5' : '#ebf8ff', color: tx.type === 'deposit' ? 'var(--success)' : tx.type === 'withdrawal' ? 'var(--danger)' : 'var(--bank-secondary)' }}>{tx.type.toUpperCase()}</span></td>
                            <td style={{ fontSize: 13 }}><div>{d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</div><div style={{ color: 'var(--text-muted)' }}>{d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div></td>
                            <td><span className="tx-status-badge completed">Completed</span></td>
                            <td style={{ textAlign: 'right' }} className={isCredit ? 'tx-amount-positive' : 'tx-amount-negative'}>{isCredit ? '+' : '-'}{fmtMoney(tx.amount)}</td>
                        </tr>);
                    })}</tbody>
                </table>
            </div>
            {pages > 1 && <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 16 }}>
                <button className="btn-secondary" style={{ padding: '6px 12px' }} disabled={page === 0} onClick={() => setPage(p => p - 1)}>Prev</button>
                <span style={{ alignSelf: 'center', fontSize: 13, color: 'var(--text-muted)' }}>Page {page + 1} of {pages}</span>
                <button className="btn-secondary" style={{ padding: '6px 12px' }} disabled={page >= pages - 1} onClick={() => setPage(p => p + 1)}>Next</button>
            </div>}
        </div>
    );
}

// ─── Loans Tab ────────────────────────────────────────────────────────────────
function LoansTab({ user, loans, setLoans, onRefresh }) {
    const [tab, setTab] = useState('list');
    const [form, setForm] = useState({ amount: '', term_months: '12', purpose: 'Personal' });
    const [repayForm, setRepayForm] = useState({ loan_id: '', amount: '' });
    const [busy, setBusy] = useState(false);
    const isVerified = user?.verification_status === 'verified';

    const applySubmit = async (e) => {
        e.preventDefault();
        setBusy(true);
        try {
            const res = await applyLoan({ amount: parseFloat(form.amount), term_months: parseInt(form.term_months), purpose: form.purpose });
            toast.success(`Loan approved! Monthly payment: ${fmtMoney(res.data.monthly_payment)}`);
            setForm({ amount: '', term_months: '12', purpose: 'Personal' });
            setTab('list');
            onRefresh();
        } catch (e) { toast.error(e.response?.data?.detail || 'Loan application failed.'); }
        finally { setBusy(false); }
    };

    const repaySubmit = async (e) => {
        e.preventDefault();
        setBusy(true);
        try {
            const res = await repayLoan({ loan_id: parseInt(repayForm.loan_id), amount: parseFloat(repayForm.amount) });
            toast.success(res.data.message);
            setRepayForm({ loan_id: '', amount: '' });
            onRefresh();
        } catch (e) { toast.error(e.response?.data?.detail || 'Repayment failed.'); }
        finally { setBusy(false); }
    };

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                <h2>Loans</h2>
                <div style={{ display: 'flex', gap: 8 }}>
                    {['list', 'apply', 'repay'].map(t => <button key={t} onClick={() => setTab(t)} className={tab === t ? 'btn-primary' : 'btn-secondary'} style={{ padding: '6px 14px', fontSize: 13 }}>{t === 'list' ? 'My Loans' : t === 'apply' ? 'Apply' : 'Repay'}</button>)}
                </div>
            </div>

            {tab === 'list' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    {loans.length === 0 && <div className="card" style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>No active loans. <br />Apply for a loan to grow your financial power.</div>}
                    {loans.map(l => (
                        <div key={l.id} className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 20 }}>
                            <div><div style={{ fontWeight: 600, fontSize: 16, marginBottom: 4 }}>{l.purpose} Loan</div><div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Original: {fmtMoney(l.amount)} | {l.term_months} months | {l.interest_rate}% p.a.</div><div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Monthly Payment: {fmtMoney(l.monthly_payment)} | Applied: {new Date(l.created_at).toLocaleDateString()}</div></div>
                            <div style={{ textAlign: 'right' }}>
                                <div style={{ fontSize: 22, fontWeight: 700, color: l.status === 'paid' ? 'var(--success)' : 'var(--bank-primary)' }}>{fmtMoney(l.balance_remaining)}</div>
                                <div style={{ fontSize: 12 }}>remaining</div>
                                <span style={{ display: 'inline-block', marginTop: 6, padding: '3px 10px', borderRadius: 12, fontSize: 11, fontWeight: 600, background: l.status === 'paid' ? '#f0fff4' : '#ebf8ff', color: l.status === 'paid' ? 'var(--success)' : 'var(--bank-secondary)' }}>{l.status.toUpperCase()}</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {tab === 'apply' && (
                <div className="card" style={{ maxWidth: 500 }}>
                    {!isVerified && <div style={{ background: '#fff5f5', border: '1px solid #fed7d7', borderRadius: 8, padding: 12, marginBottom: 20, color: 'var(--danger)', fontSize: 13 }}>KYC verification required to apply for loans.</div>}
                    <form onSubmit={applySubmit}>
                        <div style={{ marginBottom: 16 }}><label className="form-label">Loan Amount (KSh)</label><input className="form-input" style={{ width: '100%' }} type="number" min="100" max="100000" placeholder="e.g. 5000" value={form.amount} onChange={e => setForm(f => ({ ...f, amount: e.target.value }))} disabled={!isVerified} /></div>
                        <div style={{ marginBottom: 16 }}><label className="form-label">Term (months)</label><select className="form-input" style={{ width: '100%' }} value={form.term_months} onChange={e => setForm(f => ({ ...f, term_months: e.target.value }))} disabled={!isVerified}>{[6, 12, 24, 36, 60].map(m => <option key={m} value={m}>{m} months</option>)}</select></div>
                        <div style={{ marginBottom: 24 }}><label className="form-label">Purpose</label><select className="form-input" style={{ width: '100%' }} value={form.purpose} onChange={e => setForm(f => ({ ...f, purpose: e.target.value }))} disabled={!isVerified}>{['Personal', 'Business', 'Education', 'Home Improvement', 'Medical', 'Vehicle'].map(p => <option key={p} value={p}>{p}</option>)}</select></div>
                        {form.amount && form.term_months && (
                            <div style={{ background: '#ebf8ff', borderRadius: 8, padding: 12, marginBottom: 16, fontSize: 13, color: 'var(--bank-secondary)' }}>
                                Estimated monthly payment: <strong>{fmtMoney((parseFloat(form.amount) * (0.055 / 12) * Math.pow(1.055 / 12 + 1, parseInt(form.term_months))) / (Math.pow(0.055 / 12 + 1, parseInt(form.term_months)) - 1))}</strong> at 5.5% p.a.
                            </div>
                        )}
                        <button type="submit" className="btn-primary" style={{ width: '100%' }} disabled={busy || !isVerified}><Landmark size={16} /> {busy ? 'Processing...' : 'Submit Application'}</button>
                    </form>
                </div>
            )}

            {tab === 'repay' && (
                <div className="card" style={{ maxWidth: 500 }}>
                    <form onSubmit={repaySubmit}>
                        <div style={{ marginBottom: 16 }}><label className="form-label">Select Loan</label>
                            <select className="form-input" style={{ width: '100%' }} value={repayForm.loan_id} onChange={e => setRepayForm(f => ({ ...f, loan_id: e.target.value }))}>
                                <option value="">— Select active loan —</option>
                                {loans.filter(l => l.status === 'active').map(l => <option key={l.id} value={l.id}>{l.purpose} | Remaining: {fmtMoney(l.balance_remaining)}</option>)}
                            </select>
                        </div>
                        <div style={{ marginBottom: 24 }}><label className="form-label">Repayment Amount</label><input className="form-input" style={{ width: '100%' }} type="number" min="1" placeholder="0.00" value={repayForm.amount} onChange={e => setRepayForm(f => ({ ...f, amount: e.target.value }))} /></div>
                        <button type="submit" className="btn-primary" style={{ width: '100%' }} disabled={busy || !repayForm.loan_id}><DollarSign size={16} /> {busy ? 'Processing...' : 'Make Repayment'}</button>
                    </form>
                </div>
            )}
        </div>
    );
}

// ─── Investments/Savings Tab ───────────────────────────────────────────────────
function InvestmentsTab({ accounts, showBalance }) {
    const savings = accounts.find(a => a.account_type === 'savings');
    const checking = accounts.find(a => a.account_type === 'checking');
    return (
        <div>
            <h2 style={{ marginBottom: 24 }}>Investments & Savings</h2>
            <div className="grid-2">
                <div className="card" style={{ borderTop: '4px solid var(--bank-teal)' }}>
                    <h3 style={{ marginBottom: 8 }}>Premium Savings Account</h3>
                    <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 20 }}>High-yield savings with 3.5% APY interest, compounded monthly.</p>
                    <div style={{ fontSize: 32, fontWeight: 700, color: 'var(--bank-teal)', marginBottom: 4 }}>{showBalance ? fmtMoney(savings?.balance) : '****'}</div>
                    <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Current Balance</div>
                    <div style={{ marginTop: 20, padding: '12px 0', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                        <span style={{ color: 'var(--text-muted)' }}>Interest Rate</span><span style={{ fontWeight: 600, color: 'var(--success)' }}>3.50% APY</span>
                    </div>
                    <div style={{ padding: '12px 0', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                        <span style={{ color: 'var(--text-muted)' }}>Projected Monthly</span><span style={{ fontWeight: 600, color: 'var(--success)' }}>{showBalance ? fmtMoney((savings?.balance || 0) * 0.035 / 12) : '****'}</span>
                    </div>
                </div>
                <div className="card" style={{ borderTop: '4px solid var(--bank-accent)' }}>
                    <h3 style={{ marginBottom: 8 }}>Checking Account</h3>
                    <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 20 }}>Everyday spending, zero fees, instant transfers.</p>
                    <div style={{ fontSize: 32, fontWeight: 700, color: 'var(--bank-accent)', marginBottom: 4 }}>{showBalance ? fmtMoney(checking?.balance) : '****'}</div>
                    <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Current Balance</div>
                    <div style={{ marginTop: 20, padding: '12px 0', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                        <span style={{ color: 'var(--text-muted)' }}>Monthly Fee</span><span style={{ fontWeight: 600, color: 'var(--success)' }}>KSh 0.00</span>
                    </div>
                    <div style={{ padding: '12px 0', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                        <span style={{ color: 'var(--text-muted)' }}>Daily ATM Limit</span><span style={{ fontWeight: 600 }}>KSh 250,000</span>
                    </div>
                </div>
            </div>
            <div className="card" style={{ marginTop: 0 }}>
                <h3 style={{ marginBottom: 16 }}>Investment Portfolio</h3>
                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                    {[{ name: 'US Treasury Bond', rate: '4.8%', type: 'Fixed Income', risk: 'Low' }, { name: 'Index Fund ETF', rate: '7.2%', type: 'Equity', risk: 'Medium' }, { name: 'Money Market Fund', rate: '5.1%', type: 'Cash Equiv.', risk: 'Very Low' }].map(inv => (
                        <div key={inv.name} style={{ flex: '1 1 200px', background: '#f8fafc', borderRadius: 8, padding: 16, border: '1px solid var(--border-color)' }}>
                            <div style={{ fontWeight: 600, marginBottom: 4 }}>{inv.name}</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>{inv.type}</div>
                            <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--success)' }}>{inv.rate}</div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Risk: {inv.risk}</div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

// ─── Statements Tab ───────────────────────────────────────────────────────────
function StatementsTab() {
    const now = new Date();
    const [month, setMonth] = useState(now.getMonth() + 1);
    const [year, setYear] = useState(now.getFullYear());
    const [statement, setStatement] = useState(null);
    const [loading, setLoading] = useState(false);

    const load = async () => {
        setLoading(true);
        try {
            const res = await fetchStatement(month, year);
            setStatement(res.data);
        } catch { toast.error('Failed to load statement.'); }
        finally { setLoading(false); }
    };

    const downloadPDF = async () => {
        if (!statement) return;
        setLoading(true);
        try {
            const res = await downloadStatementPDF(month, year);
            const blob = new Blob([res.data], { type: 'application/pdf' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url;
            a.download = `Horizon_Statement_${statement.period.label.replace(' ', '_')}.pdf`;
            a.click(); URL.revokeObjectURL(url);
        } catch {
            toast.error('Failed to download PDF.');
        } finally {
            setLoading(false);
        }
    };

    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

    return (
        <div>
            <h2 style={{ marginBottom: 24 }}>Account Statements</h2>
            <div className="card" style={{ display: 'flex', gap: 16, alignItems: 'flex-end', marginBottom: 24, flexWrap: 'wrap' }}>
                <div><label className="form-label">Month</label><select className="form-input" value={month} onChange={e => setMonth(Number(e.target.value))}>{months.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}</select></div>
                <div><label className="form-label">Year</label><select className="form-input" value={year} onChange={e => setYear(Number(e.target.value))}>{[now.getFullYear(), now.getFullYear() - 1, now.getFullYear() - 2].map(y => <option key={y} value={y}>{y}</option>)}</select></div>
                <button className="btn-primary" onClick={load} disabled={loading}><BookOpen size={16} />{loading ? 'Loading...' : 'Generate Statement'}</button>
            </div>

            {statement && (
                <div className="card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                        <div><h3 style={{ margin: 0 }}>Statement: {statement.period.label}</h3><p style={{ margin: '4px 0 0', color: 'var(--text-muted)', fontSize: 13 }}>{statement.summary.transaction_count} transactions</p></div>
                        <div style={{ display: 'flex', gap: 8 }}>
                            <button className="btn-secondary" onClick={downloadPDF} disabled={loading} style={{ display: 'flex', gap: 8, alignItems: 'center' }}><Download size={16} /> Download PDF</button>
                        </div>
                    </div>
                    <div className="grid-4" style={{ marginBottom: 20 }}>
                        <div className="summary-card"><h2>Total Credits</h2><div className="value" style={{ color: 'var(--success)' }}>{fmtMoney(statement.summary.total_credits)}</div></div>
                        <div className="summary-card"><h2>Total Debits</h2><div className="value" style={{ color: 'var(--danger)' }}>{fmtMoney(statement.summary.total_debits)}</div></div>
                        <div className="summary-card"><h2>Net Change</h2><div className="value" style={{ color: statement.summary.net >= 0 ? 'var(--success)' : 'var(--danger)' }}>{fmtMoney(statement.summary.net)}</div></div>
                        <div className="summary-card"><h2>Transactions</h2><div className="value">{statement.summary.transaction_count}</div></div>
                    </div>
                    {statement.transactions.length > 0 && (
                        <div className="tx-table-container">
                            <table className="tx-table"><thead><tr><th>Description</th><th>Date</th><th>Type</th><th style={{ textAlign: 'right' }}>Amount</th></tr></thead>
                                <tbody>{statement.transactions.map(t => (
                                    <tr key={t.id}><td style={{ fontSize: 13 }}>{(t.description || '').split('|')[0]}</td><td style={{ fontSize: 13 }}>{new Date(t.timestamp).toLocaleDateString()}</td><td><span className="tx-status-badge">{t.type.toUpperCase()}</span></td><td style={{ textAlign: 'right' }} className={t.is_credit ? 'tx-amount-positive' : 'tx-amount-negative'}>{t.is_credit ? '+' : '-'}{fmtMoney(t.amount)}</td></tr>
                                ))}</tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

// ─── Notifications Tab ────────────────────────────────────────────────────────
function NotificationsTab({ notifications, setNotifications }) {
    const markRead = async (id) => {
        try { await markNotificationRead(id); setNotifications(n => n.map(x => x.id === id ? { ...x, is_read: true } : x)); } catch { }
    };
    const markAll = async () => {
        try { await markAllNotificationsRead(); setNotifications(n => n.map(x => ({ ...x, is_read: true }))); toast.success('All marked as read'); } catch { }
    };
    const unread = notifications.filter(n => !n.is_read).length;
    const catColor = { info: 'var(--bank-accent)', success: 'var(--success)', alert: 'var(--danger)' };

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                <h2>Notifications {unread > 0 && <span style={{ background: 'var(--danger)', color: 'white', borderRadius: '50%', padding: '2px 8px', fontSize: 12, marginLeft: 8 }}>{unread}</span>}</h2>
                {unread > 0 && <button className="btn-secondary" style={{ fontSize: 13, padding: '6px 14px' }} onClick={markAll}>Mark all as read</button>}
            </div>
            {notifications.length === 0 && <div className="card" style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>No notifications yet.</div>}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {notifications.map(n => (
                    <div key={n.id} className="card" onClick={() => !n.is_read && markRead(n.id)} style={{ display: 'flex', gap: 16, alignItems: 'flex-start', cursor: n.is_read ? 'default' : 'pointer', opacity: n.is_read ? 0.7 : 1, borderLeft: `4px solid ${catColor[n.category] || 'var(--bank-accent)'}`, transition: 'opacity 0.2s' }}>
                        <div style={{ flex: 1 }}>
                            <div style={{ fontWeight: n.is_read ? 400 : 600 }}>{n.message}</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{new Date(n.created_at).toLocaleString()}</div>
                        </div>
                        {!n.is_read && <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--bank-accent)', flexShrink: 0, marginTop: 6 }} />}
                    </div>
                ))}
            </div>
        </div>
    );
}

// ─── Settings Tab ─────────────────────────────────────────────────────────────
function SettingsTab({ user, onRefresh }) {
    const [profile, setProfile] = useState({ full_name: user?.full_name || '', phone: user?.phone || '', address: user?.address || '' });
    const [pwd, setPwd] = useState({ current_password: '', new_password: '', confirm: '' });
    const [showPwd, setShowPwd] = useState(false);
    const [busy, setBusy] = useState(false);
    const [tab, setTab] = useState('profile');

    const saveProfile = async (e) => {
        e.preventDefault(); setBusy(true);
        try { await updateProfile(profile); toast.success('Profile updated!'); onRefresh(); }
        catch (e) { toast.error(e.response?.data?.detail || 'Update failed.'); }
        finally { setBusy(false); }
    };

    const savePwd = async (e) => {
        e.preventDefault();
        if (pwd.new_password !== pwd.confirm) return toast.error('Passwords do not match.');
        if (pwd.new_password.length < 6) return toast.error('Password must be at least 6 characters.');
        setBusy(true);
        try { await changePassword({ current_password: pwd.current_password, new_password: pwd.new_password }); toast.success('Password changed!'); setPwd({ current_password: '', new_password: '', confirm: '' }); }
        catch (e) { toast.error(e.response?.data?.detail || 'Change failed.'); }
        finally { setBusy(false); }
    };

    return (
        <div>
            <h2 style={{ marginBottom: 24 }}>Settings</h2>
            <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
                <button onClick={() => setTab('profile')} className={tab === 'profile' ? 'btn-primary' : 'btn-secondary'} style={{ padding: '6px 16px', fontSize: 13 }}><User size={14} style={{ marginRight: 6 }} />Profile</button>
                <button onClick={() => setTab('security')} className={tab === 'security' ? 'btn-primary' : 'btn-secondary'} style={{ padding: '6px 16px', fontSize: 13 }}><Key size={14} style={{ marginRight: 6 }} />Security</button>
            </div>

            {tab === 'profile' && (
                <div className="card" style={{ maxWidth: 500 }}>
                    <form onSubmit={saveProfile}>
                        <div style={{ marginBottom: 16 }}><label className="form-label">Full Name</label><input className="form-input" style={{ width: '100%' }} value={profile.full_name} onChange={e => setProfile(f => ({ ...f, full_name: e.target.value }))} /></div>
                        <div style={{ marginBottom: 16 }}><label className="form-label">Email Address</label><input className="form-input" style={{ width: '100%', opacity: 0.6 }} value={user?.email} readOnly /></div>
                        <div style={{ marginBottom: 16 }}><label className="form-label">Phone Number</label><input className="form-input" style={{ width: '100%' }} placeholder="+1 (555) 000-0000" value={profile.phone} onChange={e => setProfile(f => ({ ...f, phone: e.target.value }))} /></div>
                        <div style={{ marginBottom: 24 }}><label className="form-label">Address</label><input className="form-input" style={{ width: '100%' }} placeholder="123 Main St, City, Country" value={profile.address} onChange={e => setProfile(f => ({ ...f, address: e.target.value }))} /></div>
                        <div style={{ marginBottom: 16, padding: '12px 16px', background: '#f8fafc', borderRadius: 8, fontSize: 13 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--text-muted)' }}>KYC Status</span><span style={{ fontWeight: 600, color: user?.verification_status === 'verified' ? 'var(--success)' : 'var(--warning)' }}>{user?.verification_status?.toUpperCase()}</span></div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}><span style={{ color: 'var(--text-muted)' }}>Member Since</span><span style={{ fontWeight: 600 }}>{user?.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}</span></div>
                        </div>
                        <button type="submit" className="btn-primary" style={{ width: '100%' }} disabled={busy}>{busy ? 'Saving...' : 'Save Changes'}</button>
                    </form>
                </div>
            )}

            {tab === 'security' && (
                <div className="card" style={{ maxWidth: 500 }}>
                    <form onSubmit={savePwd}>
                        <div style={{ marginBottom: 16 }}>
                            <label className="form-label">Current Password</label>
                            <div style={{ position: 'relative' }}>
                                <input className="form-input" style={{ width: '100%', paddingRight: 40 }} type={showPwd ? 'text' : 'password'} value={pwd.current_password} onChange={e => setPwd(f => ({ ...f, current_password: e.target.value }))} />
                                <button type="button" onClick={() => setShowPwd(v => !v)} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', color: 'var(--text-muted)' }}>{showPwd ? <EyeOff size={16} /> : <Eye size={16} />}</button>
                            </div>
                        </div>
                        <div style={{ marginBottom: 16 }}><label className="form-label">New Password</label><input className="form-input" style={{ width: '100%' }} type={showPwd ? 'text' : 'password'} value={pwd.new_password} onChange={e => setPwd(f => ({ ...f, new_password: e.target.value }))} /></div>
                        <div style={{ marginBottom: 24 }}><label className="form-label">Confirm New Password</label><input className="form-input" style={{ width: '100%' }} type={showPwd ? 'text' : 'password'} value={pwd.confirm} onChange={e => setPwd(f => ({ ...f, confirm: e.target.value }))} /></div>
                        <button type="submit" className="btn-primary" style={{ width: '100%' }} disabled={busy}><Key size={16} />{busy ? 'Changing...' : 'Change Password'}</button>
                    </form>
                </div>
            )}
        </div>
    );
}

// ─── Root Dashboard Component ─────────────────────────────────────────────────
export default function Dashboard() {
    const navigate = useNavigate();
    const [user, setUser] = useState(null);
    const [accounts, setAccounts] = useState([]);
    const [transactions, setTransactions] = useState([]);
    const [loans, setLoans] = useState([]);
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showKycPopup, setShowKycPopup] = useState(false);
    const [activeTab, setActiveTab] = useState('Dashboard');
    const [showBalance, setShowBalance] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    const loadData = useCallback(async () => {
        try {
            // Core Identity call - if this fails with 401, we logout
            const meRes = await fetchMe();
            setUser(meRes.data);
            
            if (meRes.data.role === 'admin') {
                navigate('/secure-staff-access');
                return;
            }

            // Secondary data calls - we handle these individually so one failure doesn't crash the dash
            const fetchData = async (fn, setter, name) => {
                try {
                    const res = await fn();
                    setter(res.data);
                } catch (e) {
                    console.error(`Failed to fetch ${name}:`, e);
                    if (e.response?.status === 401) throw e; // Pass 401 up to logout
                    toast.error(`Portal: Could not load ${name} (using cached/empty)`);
                }
            };

            await Promise.all([
                fetchData(fetchAccounts, setAccounts, 'accounts'),
                fetchData(fetchTransactions, setTransactions, 'transactions'),
                fetchData(fetchLoans, setLoans, 'loans'),
                fetchData(fetchNotifications, setNotifications, 'notifications')
            ]);
        } catch (err) {
            const detail = err.response?.data?.detail || 'Connection error';
            const status = err.response?.status;
            
            if (status === 401) {
                toast.error('Session expired. Please log in again.');
                logout();
                navigate('/login');
            } else {
                toast.error(`Portal error: ${detail}`);
                // Don't necessarily navigate to login for non-401 errors
                // unless it's a critical startup failure.
            }
        }
        finally { setLoading(false); }
    }, [navigate]);

    useEffect(() => { loadData(); }, [loadData]);

    const handleLogout = () => { logout(); navigate('/login'); };

    const handleVerifySubmit = async (data) => {
        try {
            await submitVerification(data);
            toast.success('KYC submitted successfully. Awaiting admin review.');
            setShowKycPopup(false);
            loadData();
        } catch (e) { toast.error(e.response?.data?.detail || 'Verification failed.'); }
    };

    if (loading) return (
        <div style={{ padding: 50, textAlign: 'center', color: 'var(--bank-primary)', fontWeight: 600 }}>
            <div>Loading Horizon Secure Portal...</div>
            <div style={{ fontSize: 10, color: '#a0aec0', marginTop: 10 }}>Frontend v2.2 | API check...</div>
        </div>
    );

    const isVerified = user?.verification_status === 'verified';
    const unreadCount = notifications.filter(n => !n.is_read).length;

    const navItems = [
        { label: 'Dashboard', icon: <LayoutDashboard size={18} /> },
        { label: 'Accounts', icon: <CreditCard size={18} /> },
        { label: 'Transfers', icon: <ArrowRightLeft size={18} /> },
        { label: 'Transactions', icon: <History size={18} /> },
        { label: 'Loans', icon: <Landmark size={18} /> },
        { label: 'Investments', icon: <TrendingUp size={18} /> },
        { label: 'Statements', icon: <FileText size={18} /> },
    ];
    const bottomItems = [
        { label: 'Notifications', icon: <Bell size={18} />, badge: unreadCount },
        { label: 'Settings', icon: <Settings size={18} /> },
    ];

    const renderContent = () => {
        switch (activeTab) {
            case 'Dashboard': return <DashboardTab user={user} accounts={accounts} transactions={transactions} showBalance={showBalance} />;
            case 'Accounts': return <AccountsTab accounts={accounts} onRefresh={loadData} showBalance={showBalance} />;
            case 'Transfers': return <TransfersTab user={user} accounts={accounts} onRefresh={loadData} showBalance={showBalance} />;
            case 'Transactions': return <TransactionsTab transactions={transactions} accounts={accounts} />;
            case 'Loans': return <LoansTab user={user} loans={loans} setLoans={setLoans} onRefresh={loadData} />;
            case 'Investments': return <InvestmentsTab accounts={accounts} showBalance={showBalance} />;
            case 'Statements': return <StatementsTab />;
            case 'Notifications': return <NotificationsTab notifications={notifications} setNotifications={setNotifications} />;
            case 'Settings': return <SettingsTab user={user} onRefresh={loadData} />;
            default: return null;
        }
    };

    return (
        <div className="dashboard-layout">
            {mobileMenuOpen && <div className={`mobile-overlay ${mobileMenuOpen ? 'mobile-open' : ''}`} onClick={() => setMobileMenuOpen(false)}></div>}

            <aside className={`sidebar ${mobileMenuOpen ? 'mobile-open' : ''}`}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 40 }}>
                    <h1 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 12, fontSize: 20 }}><span className="sidebar-logo-icon">H</span> HORIZON</h1>
                    <button className="sidebar-close-btn" onClick={() => setMobileMenuOpen(false)}><X size={24} /></button>
                </div>
                <ul className="sidebar-nav">
                    {navItems.map(item => (
                        <li key={item.label} className={`sidebar-item ${activeTab === item.label ? 'active' : ''}`} onClick={() => { setActiveTab(item.label); setMobileMenuOpen(false); }}>
                            {item.icon} {item.label}
                        </li>
                    ))}
                </ul>
                <ul className="sidebar-nav" style={{ marginTop: 'auto', flex: 0, gap: 4 }}>
                    {bottomItems.map(item => (
                        <li key={item.label} className={`sidebar-item ${activeTab === item.label ? 'active' : ''}`} onClick={() => { setActiveTab(item.label); setMobileMenuOpen(false); }} style={{ position: 'relative' }}>
                            {item.icon} {item.label}
                            {item.badge > 0 && <span style={{ position: 'absolute', right: 12, background: 'var(--danger)', color: 'white', borderRadius: '50%', width: 18, height: 18, fontSize: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700 }}>{item.badge}</span>}
                        </li>
                    ))}
                    <li className="sidebar-item logout" onClick={handleLogout}><LogOut size={18} /> Logout</li>
                </ul>
            </aside>

            <main className="main-content">
                <header className="top-header">
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                        <button className="mobile-menu-btn" onClick={() => setMobileMenuOpen(true)}>
                            <Menu size={24} />
                        </button>
                        <div>
                            <h2 className="top-header-title">Welcome back, {user?.full_name?.split(' ')[0]}</h2>
                            <p style={{ color: 'var(--text-muted)', marginTop: 4 }}>Here is what's happening with your account today.</p>
                        </div>
                    </div>
                    <div className="user-profile-badge">
                        <button onClick={() => setShowBalance(!showBalance)} style={{ cursor: 'pointer', background: 'transparent', border: 'none', color: 'var(--bank-primary)', display: 'flex', alignItems: 'center', padding: 0, marginRight: 8 }}>
                            {showBalance ? <Eye size={18} /> : <EyeOff size={18} />}
                        </button>
                        <div style={{ fontWeight: 600, color: 'var(--bank-primary)' }}>{user?.full_name}</div>
                        {isVerified ? <span className="verification-status status-verified"><CheckCircle2 size={14} /> Verified</span>
                            : user?.verification_status === 'pending' ? <span className="verification-status status-pending">Pending Review</span>
                                : <span className="verification-status status-unverified">Unverified</span>}
                    </div>
                </header>

                {!isVerified && user?.verification_status !== 'pending' && (
                    <div className="verification-banner">
                        <div className="banner-content"><div className="banner-icon"><AlertTriangle size={24} /></div><div className="banner-text"><h3>Action Required: Identity Verification</h3><p>Complete KYC to unlock transfers, loans, and full features.</p></div></div>
                        <button onClick={() => setShowKycPopup(true)} className="btn-verify"><RefreshCcw size={18} /> Verify Identity Now</button>
                    </div>
                )}

                {showKycPopup && <KycPopup onClose={() => setShowKycPopup(false)} onSubmit={handleVerifySubmit} />}

                {renderContent()}
            </main>
        </div>
    );
}
