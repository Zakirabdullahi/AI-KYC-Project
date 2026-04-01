import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { Shield, Mail, Lock, User } from 'lucide-react';
import { registerUser } from '../api';
import styles from './Auth.module.css';

export default function Register() {
    const navigate = useNavigate();
    const [formData, setForm] = useState({ full_name: '', email: '', password: '' });
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            await registerUser(formData);
            toast.success('Account created successfully. Please sign in to begin identity verification.');
            navigate('/login');
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Registration failed');
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
                <p className={styles.subtitle}>Open your secure account today</p>

                <form onSubmit={handleSubmit} className={styles.form}>
                    <div className={styles.inputGroup}>
                        <User size={18} className={styles.inputIcon} />
                        <input
                            type="text"
                            placeholder="Legal Full Name"
                            value={formData.full_name}
                            onChange={e => setForm({ ...formData, full_name: e.target.value })}
                            required
                        />
                    </div>
                    <div className={styles.inputGroup}>
                        <Mail size={18} className={styles.inputIcon} />
                        <input
                            type="email"
                            placeholder="Email Address"
                            value={formData.email}
                            onChange={e => setForm({ ...formData, email: e.target.value })}
                            required
                        />
                    </div>
                    <div className={styles.inputGroup}>
                        <Lock size={18} className={styles.inputIcon} />
                        <input
                            type="password"
                            placeholder="Secure Password"
                            value={formData.password}
                            onChange={e => setForm({ ...formData, password: e.target.value })}
                            required
                        />
                    </div>

                    <button type="submit" className={`btn-primary ${styles.submitBtn}`} disabled={loading}>
                        {loading ? 'Creating Identity...' : 'Open Account'}
                    </button>
                </form>

                <div className={styles.authFooter}>
                    <p>Already have an account? <Link to="/login">Sign in</Link></p>
                </div>
            </div>
        </div>
    );
}
