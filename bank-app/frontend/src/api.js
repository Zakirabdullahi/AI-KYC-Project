import axios from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const api = axios.create({
    baseURL,
});

api.interceptors.request.use(config => {
    const token = localStorage.getItem('bank_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// ── Auth ──────────────────────────────────────────────────────────────────────
export const registerUser = (data) => api.post('/auth/register', data);
export const loginUser = (data) => api.post('/auth/token', data);
export const fetchMe = () => api.get('/users/me');
export const updateProfile = (data) => api.patch('/users/me/profile', data);
export const changePassword = (data) => api.post('/users/me/change-password', data);

// ── Banking ───────────────────────────────────────────────────────────────────
export const fetchAccounts = () => api.get('/banking/accounts');
export const fetchTransactions = () => api.get('/banking/transactions');
export const executeTransfer = (data) => api.post('/banking/transfer', data);
export const addFunds = (data) => api.post('/banking/add-funds', data);
export const withdrawFunds = (data) => api.post('/banking/withdraw', data);

// ── Loans ─────────────────────────────────────────────────────────────────────
export const fetchLoans = () => api.get('/banking/loans');
export const applyLoan = (data) => api.post('/banking/loans/apply', data);
export const repayLoan = (data) => api.post('/banking/loans/repay', data);

// ── Statements ────────────────────────────────────────────────────────────────
export const fetchStatement = (month, year) => api.get(`/banking/statements?month=${month}&year=${year}`);
export const downloadStatementPDF = (month, year) => api.get(`/banking/statements/pdf?month=${month}&year=${year}`, { responseType: 'blob' });

// ── Notifications ─────────────────────────────────────────────────────────────
export const fetchNotifications = () => api.get('/notifications');
export const markNotificationRead = (id) => api.patch(`/notifications/${id}/read`);
export const markAllNotificationsRead = () => api.patch('/notifications/read-all');

// ── Verification ──────────────────────────────────────────────────────────────
export const submitVerification = (data) => api.post('/verify/submit', data);
export const checkVerificationStatus = () => api.get('/verify/status');

// ── Admin ─────────────────────────────────────────────────────────────────────
export const fetchAdminStats = () => api.get('/admin/stats');
export const fetchAllUsers = (q = '', status = '') => api.get(`/admin/users?q=${q}&status=${status}`);
export const fetchUserDetails = (userId) => api.get(`/admin/users/${userId}`);
export const fetchUserKycDocs = (userId) => api.get(`/admin/users/${userId}/kyc-docs`);
export const adminAdjustBalance = (userId, data) => api.post(`/admin/users/${userId}/adjust-balance`, data);
export const fetchPendingVerifications = () => api.get('/admin/pending-verifications');
export const decideVerification = (userId, decision) => api.post(`/admin/verify-user/${userId}`, { decision });
export const fetchAllTransactions = (type = '') => api.get(`/admin/transactions?type=${type}`);
export const adminResetPassword = (userId, newPassword) => api.post(`/admin/users/${userId}/reset-password`, { new_password: newPassword });
export const deleteUserKycDocs = (userId) => api.delete(`/admin/users/${userId}/kyc-docs`);

export const logout = () => {
    localStorage.removeItem('bank_token');
    localStorage.removeItem('bank_role');
};
