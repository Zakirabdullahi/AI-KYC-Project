import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Camera, Upload, X, CheckCircle2, Loader2, Shield, Zap } from 'lucide-react';

const LIVENESS_API = import.meta.env.VITE_KYC_API_URL || 'http://localhost:8001';

const COUNTRY_ID_TYPES = {
    KE: ['NATIONAL_ID', 'PASSPORT', 'ALIEN_CARD'],
    NG: ['NIN', 'BVN', 'PASSPORT', 'DRIVERS_LICENSE', 'VOTER_ID'],
    GH: ['VOTER_ID', 'DRIVER_LICENSE', 'SSNIT', 'PASSPORT'],
    ZA: ['NATIONAL_ID', 'PASSPORT', 'DRIVERS_LICENSE'],
    UG: ['NATIONAL_ID', 'PASSPORT'],
    TZ: ['NATIONAL_ID', 'PASSPORT'],
    RW: ['NATIONAL_ID', 'PASSPORT'],
    US: ['DRIVERS_LICENSE', 'PASSPORT'],
    GB: ['PASSPORT', 'DRIVERS_LICENSE'],
    OTHER: ['PASSPORT', 'NATIONAL_ID'],
};
const COUNTRY_NAMES = { KE: 'Kenya', NG: 'Nigeria', GH: 'Ghana', ZA: 'South Africa', UG: 'Uganda', TZ: 'Tanzania', RW: 'Rwanda', US: 'United States', GB: 'United Kingdom', OTHER: 'Other' };

// ─── Step Progress Bar ───────────────────────────────────────────────────────
function StepBar({ current, total }) {
    return (
        <div style={{ display: 'flex', gap: '6px', marginBottom: '24px' }}>
            {Array.from({ length: total }).map((_, i) => (
                <div key={i} style={{
                    flex: 1, height: '4px', borderRadius: '4px',
                    background: i < current ? '#002b5c' : '#e2e8f0',
                    transition: 'background 0.3s'
                }} />
            ))}
        </div>
    );
}

// ─── Document Upload Card ────────────────────────────────────────────────────
function DocUpload({ id, label, value, onChange }) {
    return (
        <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '8px', color: '#4a5568' }}>{label}</label>
            <div
                style={{ border: `2px dashed ${value ? '#38a169' : '#cbd5e0'}`, padding: '20px', textAlign: 'center', borderRadius: '8px', cursor: 'pointer', background: value ? '#f0fff4' : '#fafafa', transition: 'all 0.2s' }}
                onClick={() => document.getElementById(id).click()}
            >
                {value
                    ? <CheckCircle2 size={28} color="#38a169" style={{ margin: '0 auto 8px' }} />
                    : <Upload size={28} color="#a0aec0" style={{ margin: '0 auto 8px' }} />}
                <p style={{ fontSize: '13px', color: value ? '#276749' : '#4a5568', margin: 0 }}>
                    {value ? '✓ Uploaded successfully' : 'Click to upload'}
                </p>
                <input type="file" id={id} accept="image/*" style={{ display: 'none' }} onChange={onChange} />
            </div>
        </div>
    );
}

// ─── Main KYC Popup ──────────────────────────────────────────────────────────
export default function KycPopup({ onClose, onSubmit }) {
    const [idNumber, setIdNumber] = useState('');
    const [country, setCountry] = useState('KE');
    const [idType, setIdType] = useState('NATIONAL_ID');
    const [frontDoc, setFrontDoc] = useState(null);
    const [backDoc, setBackDoc] = useState(null);
    const [step, setStep] = useState(1); // 1=doc upload, 2=liveness, 3=done
    const [verifyResult, setVerifyResult] = useState(null); // result from backend

    // Liveness state
    const [livenessStatus, setLivenessStatus] = useState('idle');
    const [seqIndex, setSeqIndex] = useState(0);
    const SEQUENCE = [
        { id: 'left', text: 'Please turn your head to the LEFT 👈' },
        { id: 'right', text: 'Please turn your head to the RIGHT 👉' },
        { id: 'smile', text: 'Please look straight and show a big smile 😊' }
    ];
    const [capturedFrames, setCapturedFrames] = useState({ left: null, right: null, smile: null });
    const [submitting, setSubmitting] = useState(false);

    const videoRef = useRef(null);
    const streamRef = useRef(null);
    const intervalRef = useRef(null);
    const canvasRef = useRef(null);

    const handleFileRead = (e, setter) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onloadend = () => setter(reader.result);
        reader.readAsDataURL(file);
    };

    // ── Start webcam ──────────────────────────────────────────────────────────
    const startCamera = useCallback(async () => {
        try {
            const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: 480, height: 360 } });
            streamRef.current = s;
            if (videoRef.current) videoRef.current.srcObject = s;
        } catch (err) {
            setLivenessStatus('offline');
        }
    }, []);

    const stopCamera = useCallback(() => {
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(t => t.stop());
            streamRef.current = null;
        }
        if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
        }
    }, []);

    // ── Start Liveness ─────────────────────────
    const fetchChallenge = useCallback(async () => {
        setLivenessStatus('challenge');
        setSeqIndex(0);
        setCapturedFrames({ left: null, right: null, smile: null });
    }, []);

    // ── Capture a frame and send it to the liveness API ──────────────────────
    const captureAndVerify = useCallback(async () => {
        if (!videoRef.current || !canvasRef.current) return;

        // Use a functional state update to safely grab the CURRENT index 
        setSeqIndex(currentIndex => {
            const currentChallenge = SEQUENCE[currentIndex];
            if (!currentChallenge) return currentIndex;

            const ctx = canvasRef.current.getContext('2d');
            canvasRef.current.width = videoRef.current.videoWidth;
            canvasRef.current.height = videoRef.current.videoHeight;
            ctx.drawImage(videoRef.current, 0, 0);
            const frame = canvasRef.current.toDataURL('image/jpeg', 0.7);

            fetch(`${LIVENESS_API}/api/liveness/verify`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ frame, challenge: currentChallenge.id })
            }).then(res => res.json()).then(data => {
                if (data.success) {
                    setCapturedFrames(prev => ({ ...prev, [currentChallenge.id]: frame }));
                    if (currentIndex < SEQUENCE.length - 1) {
                        setSeqIndex(currentIndex + 1); // Advance to next challenge
                    } else {
                        // Entire sequence finished
                        if (intervalRef.current) {
                            clearInterval(intervalRef.current);
                            intervalRef.current = null;
                        }
                        setLivenessStatus('passed');
                        stopCamera();
                    }
                }
            }).catch(() => {
                // Ignore network blips, retry next frame
            });

            return currentIndex;
        });
    }, [stopCamera]);

    // ── Start sending frames when challenge is active ─────────────────────────
    useEffect(() => {
        if (livenessStatus === 'challenge') {
            if (intervalRef.current) clearInterval(intervalRef.current);
            intervalRef.current = setInterval(captureAndVerify, 500); // every 500ms
        }
        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
        };
    }, [livenessStatus, captureAndVerify]);

    // ── Enter liveness step ───────────────────────────────────────────────────
    const enterLiveness = async () => {
        setStep(2);
        await startCamera();
        await fetchChallenge();
    };

    // ── Cleanup on unmount ────────────────────────────────────────────────────
    useEffect(() => () => stopCamera(), [stopCamera]);

    // ── Final submit ──────────────────────────────────────────────────────────
    const handleFinalSubmit = async () => {
        if (!idNumber || !frontDoc || !backDoc || !capturedFrames.smile) return;
        setSubmitting(true);
        try {
            const result = await onSubmit({
                id_number: idNumber,
                country: country,
                id_type: idType,
                front_doc_b64: frontDoc,
                back_doc_b64: backDoc,
                selfie_image_b64: capturedFrames.smile,
                selfie_image_left_b64: capturedFrames.left,
                selfie_image_right_b64: capturedFrames.right
            });
            if (result) setVerifyResult(result);
        } finally {
            setSubmitting(false);
        }
    };

    // ─── Render ───────────────────────────────────────────────────────────────
    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
            backgroundColor: 'rgba(0, 43, 92, 0.7)', backdropFilter: 'blur(4px)',
            display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000
        }}>
            <div style={{
                background: 'white', padding: '32px', borderRadius: '16px', width: '100%', maxWidth: '520px',
                boxShadow: '0 25px 60px -12px rgba(0, 0, 0, 0.4)', position: 'relative', maxHeight: '90vh', overflowY: 'auto'
            }}>
                <button onClick={() => { stopCamera(); onClose(); }} style={{ position: 'absolute', top: '16px', right: '16px', background: 'transparent', border: 'none', cursor: 'pointer', color: '#718096' }}>
                    <X size={24} />
                </button>

                {/* Header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                    <div style={{ background: '#002b5c', padding: '8px', borderRadius: '8px' }}>
                        <Shield size={20} color="white" />
                    </div>
                    <div>
                        <h2 style={{ margin: 0, color: '#002b5c', fontSize: '20px' }}>Identity Verification (KYC)</h2>
                        <p style={{ margin: 0, color: '#718096', fontSize: '13px' }}>Powered by <strong style={{ color: '#004c97' }}>Smile Identity</strong> + AI Liveness Detection</p>
                    </div>
                </div>

                <StepBar current={step} total={3} />

                {/* ── Step 1: Document Upload ──────────────────────────────── */}
                {step === 1 && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                        <h3 style={{ margin: '0 0 4px', color: '#2d3748' }}>Step 1: Identity Document</h3>
                        <p style={{ margin: 0, fontSize: '13px', color: '#718096' }}>Upload a government-issued ID. Smile Identity will verify it automatically.</p>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                            <div>
                                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px', color: '#4a5568' }}>Country</label>
                                <select value={country} onChange={e => { setCountry(e.target.value); setIdType(COUNTRY_ID_TYPES[e.target.value]?.[0] || 'PASSPORT'); }} style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #e2e8f0', background: 'white', fontSize: 13 }}>
                                    {Object.entries(COUNTRY_NAMES).map(([code, name]) => <option key={code} value={code}>{name}</option>)}
                                </select>
                            </div>
                            <div>
                                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px', color: '#4a5568' }}>ID Type</label>
                                <select value={idType} onChange={e => setIdType(e.target.value)} style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #e2e8f0', background: 'white', fontSize: 13 }}>
                                    {(COUNTRY_ID_TYPES[country] || ['PASSPORT']).map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
                                </select>
                            </div>
                        </div>

                        <div>
                            <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px', color: '#4a5568' }}>ID Number <span style={{ color: '#e53e3e' }}>*</span></label>
                            <input type="text" value={idNumber} onChange={(e) => setIdNumber(e.target.value)} placeholder={`Enter your ${idType.replace(/_/g, ' ')} number`} style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #e2e8f0', boxSizing: 'border-box', fontSize: 14 }} />
                        </div>

                        <DocUpload id="frontDoc" label="Front of ID" value={frontDoc} onChange={(e) => handleFileRead(e, setFrontDoc)} />
                        <DocUpload id="backDoc" label="Back of ID" value={backDoc} onChange={(e) => handleFileRead(e, setBackDoc)} />

                        <div style={{ background: '#ebf8ff', border: '1px solid #bee3f8', borderRadius: 8, padding: '10px 14px', fontSize: 12, color: '#2b6cb0', display: 'flex', alignItems: 'center', gap: 8 }}>
                            <Zap size={14} />
                            <span>Smile Identity will automatically verify your ID against government records.</span>
                        </div>

                        <button onClick={enterLiveness} disabled={!idNumber || !frontDoc || !backDoc} className="btn-primary" style={{ padding: '14px', opacity: (!idNumber || !frontDoc || !backDoc) ? 0.5 : 1 }}>
                            Continue to Liveness Check →
                        </button>
                    </div>
                )}

                {/* ── Step 2: Live Liveness Check ─────────────────────────── */}
                {step === 2 && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        <h3 style={{ margin: '0 0 4px', color: '#2d3748' }}>Step 2: Liveness Verification</h3>

                        {/* Webcam view */}
                        <div style={{ position: 'relative', borderRadius: '10px', overflow: 'hidden', background: '#000', aspectRatio: '4/3' }}>
                            <video ref={videoRef} autoPlay muted playsInline style={{ width: '100%', height: '100%', objectFit: 'cover', transform: 'scaleX(-1)' }} />
                            <canvas ref={canvasRef} style={{ display: 'none' }} />

                            {/* Overlay */}
                            {livenessStatus === 'loading' && (
                                <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.6)', color: 'white', gap: '12px' }}>
                                    <Loader2 size={36} style={{ animation: 'spin 1s linear infinite' }} />
                                    <p style={{ margin: 0 }}>Loading AI models...</p>
                                </div>
                            )}

                            {livenessStatus === 'challenge' && SEQUENCE[seqIndex] && (
                                <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: '12px 16px', background: 'linear-gradient(to top, rgba(0,0,0,0.85), transparent)' }}>
                                    <p style={{ color: 'white', margin: 0, fontWeight: 600, fontSize: '16px', textAlign: 'center' }}>
                                        {SEQUENCE[seqIndex].text}
                                    </p>
                                    <div style={{ display: 'flex', gap: 6, justifyContent: 'center', marginTop: 10 }}>
                                        {SEQUENCE.map((s, i) => (
                                            <div key={i} style={{ width: 8, height: 8, borderRadius: '50%', background: i < seqIndex ? '#68d391' : i === seqIndex ? '#63b3ed' : '#4a5568', transition: 'background 0.3s' }} />
                                        ))}
                                    </div>
                                    <p style={{ color: '#90cdf4', margin: '4px 0 0', fontSize: '12px', textAlign: 'center' }}>
                                        Step {seqIndex + 1} of 3: Python AI is analyzing your expressions...
                                    </p>
                                </div>
                            )}

                            {livenessStatus === 'passed' && (
                                <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'rgba(0, 80, 0, 0.7)', color: 'white', gap: '12px' }}>
                                    <CheckCircle2 size={56} color="#68d391" />
                                    <p style={{ margin: 0, fontWeight: 700, fontSize: '18px' }}>Liveness Verified!</p>
                                </div>
                            )}

                            {livenessStatus === 'offline' && (
                                <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'rgba(120,0,0,0.7)', color: 'white', gap: '12px', padding: '24px', textAlign: 'center' }}>
                                    <p style={{ margin: 0, fontWeight: 700 }}>⚠ AI Service Unavailable</p>
                                    <p style={{ margin: 0, fontSize: '13px', opacity: 0.8 }}>Start the liveness microservice:<br /><code style={{ fontSize: '11px', background: 'rgba(0,0,0,0.4)', padding: '4px 8px', borderRadius: '4px', display: 'inline-block', marginTop: '6px' }}>cd kycsyst && .\.venv\Scripts\python api.py</code></p>
                                    <button onClick={fetchChallenge} style={{ background: 'white', color: '#c00', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', marginTop: '8px', fontWeight: 600, fontSize: '13px' }}>Retry Connection</button>
                                </div>
                            )}
                        </div>

                        {/* Challenge badge */}
                        {livenessStatus === 'challenge' && SEQUENCE[seqIndex] && (
                            <div style={{ background: '#ebf8ff', border: '1px solid #90cdf4', borderRadius: '8px', padding: '10px 16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <Camera size={16} color="#2b6cb0" />
                                <div style={{ fontSize: '13px', color: '#2b6cb0' }}>
                                    <strong>Challenge {seqIndex + 1}/3:</strong> {SEQUENCE[seqIndex].text}
                                </div>
                            </div>
                        )}

                        <div style={{ display: 'flex', gap: '10px', marginTop: '4px' }}>
                            <button onClick={() => { stopCamera(); setStep(1); setLivenessStatus('idle'); }} style={{ flex: 1, padding: '12px', background: '#e2e8f0', color: '#4a5568', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600 }}>← Back</button>
                            <button
                                onClick={() => setStep(3)}
                                disabled={livenessStatus !== 'passed'}
                                className="btn-primary"
                                style={{ flex: 2, padding: '12px', opacity: livenessStatus !== 'passed' ? 0.4 : 1 }}
                            >
                                Continue to Submit →
                            </button>
                        </div>
                    </div>
                )}

                {/* ── Step 3: Confirmation & Submit ────────────────────────── */}
                {step === 3 && !verifyResult && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', textAlign: 'center' }}>
                        <h3 style={{ margin: 0, color: '#2d3748' }}>Step 3: Submit for Verification</h3>

                        <div style={{ background: '#f0fff4', border: '1px solid #c6f6d5', borderRadius: '10px', padding: '24px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
                            <CheckCircle2 size={40} color="#38a169" />
                            <p style={{ margin: 0, fontWeight: 600, color: '#276749', fontSize: '16px' }}>Ready to submit!</p>
                            <div style={{ fontSize: '13px', color: '#4a5568', textAlign: 'left', width: '100%' }}>
                                <p style={{ margin: '4px 0' }}>✅ <strong>Country:</strong> {COUNTRY_NAMES[country]}</p>
                                <p style={{ margin: '4px 0' }}>✅ <strong>ID Type:</strong> {idType.replace(/_/g, ' ')}</p>
                                <p style={{ margin: '4px 0' }}>✅ <strong>ID Number:</strong> {idNumber}</p>
                                <p style={{ margin: '4px 0' }}>✅ <strong>Documents:</strong> Front + Back uploaded</p>
                                <p style={{ margin: '4px 0' }}>✅ <strong>Liveness check:</strong> Passed</p>
                            </div>
                        </div>

                        <div style={{ background: '#ebf8ff', border: '1px solid #bee3f8', borderRadius: 8, padding: '10px 14px', fontSize: 12, color: '#2b6cb0' }}>
                            <Zap size={13} style={{ display: 'inline', marginRight: 6 }} />
                            Smile Identity will check your ID against government records automatically.
                        </div>

                        <div style={{ display: 'flex', gap: '12px' }}>
                            <button onClick={() => setStep(2)} style={{ flex: 1, padding: '12px', background: '#e2e8f0', color: '#4a5568', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600 }}>← Back</button>
                            <button onClick={handleFinalSubmit} disabled={submitting} className="btn-primary" style={{ flex: 2, padding: '12px' }}>
                                {submitting ? <><Loader2 size={16} style={{ display: 'inline', animation: 'spin 1s linear infinite', marginRight: 6 }} />Verifying with Smile ID...</> : '🔍 Verify Identity'}
                            </button>
                        </div>
                    </div>
                )}

                {/* ── Step 3 Result: Smile ID returned ──────────────────────── */}
                {step === 3 && verifyResult && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', textAlign: 'center' }}>
                        {verifyResult.status === 'verified' ? (
                            <div style={{ background: '#f0fff4', border: '2px solid #68d391', borderRadius: 12, padding: 28 }}>
                                <CheckCircle2 size={48} color="#38a169" style={{ margin: '0 auto 12px' }} />
                                <h3 style={{ color: '#276749', margin: '0 0 8px' }}>Identity Verified! 🎉</h3>
                                <p style={{ color: '#4a5568', fontSize: 13, margin: 0 }}>Smile Identity automatically verified your identity.</p>
                                {verifyResult.smile_id?.confidence && <p style={{ color: '#276749', fontWeight: 700, marginTop: 8 }}>Confidence: {verifyResult.smile_id.confidence.toFixed(1)}%</p>}
                                <p style={{ fontSize: 12, color: '#718096', marginTop: 8 }}>All banking features are now unlocked. Close this window to continue.</p>
                            </div>
                        ) : verifyResult.status === 'rejected' ? (
                            <div style={{ background: '#fff5f5', border: '2px solid #fc8181', borderRadius: 12, padding: 28 }}>
                                <X size={48} color="#e53e3e" style={{ margin: '0 auto 12px' }} />
                                <h3 style={{ color: '#c53030', margin: '0 0 8px' }}>Verification Failed</h3>
                                <p style={{ color: '#4a5568', fontSize: 13 }}>{verifyResult.message}</p>
                                {verifyResult.smile_id?.result_text && <p style={{ fontSize: 12, color: '#718096' }}>Reason: {verifyResult.smile_id.result_text}</p>}
                                <button onClick={() => { setVerifyResult(null); setStep(1); setFrontDoc(null); setBackDoc(null); setSelfieB64(null); setIdNumber(''); }} className="btn-primary" style={{ marginTop: 16, background: '#e53e3e' }}>Try Again</button>
                            </div>
                        ) : (
                            <div style={{ background: '#fffbeb', border: '2px solid #f6ad55', borderRadius: 12, padding: 28 }}>
                                <Shield size={48} color="#d69e2e" style={{ margin: '0 auto 12px' }} />
                                <h3 style={{ color: '#b7791f', margin: '0 0 8px' }}>Submitted for Review</h3>
                                <p style={{ color: '#4a5568', fontSize: 13 }}>{verifyResult.message}</p>
                                <p style={{ fontSize: 12, color: '#718096' }}>You will receive a notification once an admin reviews your documents.</p>
                            </div>
                        )}
                        <button onClick={onClose} style={{ padding: 12, background: '#e2e8f0', color: '#4a5568', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}>Close</button>
                    </div>
                )}
            </div>

            <style>{`
                @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
            `}</style>
        </div>
    );
}
