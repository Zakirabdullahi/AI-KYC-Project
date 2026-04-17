import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { Shield, Mail, Lock } from 'lucide-react';
import { loginUser } from '../api';
import styles from './Auth.module.css';

export default function Login() {
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const res = await loginUser({ email, password });
            localStorage.setItem('bank_token', res.data.access_token);
            toast.success('Secure login successful');

            if (res.data.role === 'admin') {
                navigate('/secure-staff-access');
            } else {
                navigate('/dashboard');
            }
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Invalid credentials');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={styles.authWrapper}>
            <div className={styles.authCard}>
                <div className={styles.logo}>
                    <Shield size={32} className={styles.logoIcon} />
                    <h2>Horizon Bank</h2>
                </div>
                <p className={styles.subtitle}>Secure Online Banking</p>

                <form onSubmit={handleSubmit} className={styles.form}>
                    <div className={styles.inputGroup}>
                        <Mail size={18} className={styles.inputIcon} />
                        <input
                            type="email"
                            placeholder="Email Address"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            required
                        />
                    </div>
                    <div className={styles.inputGroup}>
                        <Lock size={18} className={styles.inputIcon} />
                        <input
                            type="password"
                            placeholder="Password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            required
                        />
                    </div>

                    <button type="submit" className={`btn-primary ${styles.submitBtn}`} disabled={loading}>
                        {loading ? 'Authenticating...' : 'Secure Sign In'}
                    </button>
                </form>

                <div className={styles.authFooter}>
                    <p>New to Horizon Bank? <Link to="/register">Create an account</Link></p>
                    <div style={{ fontSize: 10, color: '#a0aec0', marginTop: 12, opacity: 0.6 }}>Deployed Version: v2.4 (Resilience Patch)</div>
                </div>
            </div>
        </div>
    );
}
