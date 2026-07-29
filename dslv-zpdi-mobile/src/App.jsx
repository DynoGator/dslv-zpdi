import React, { useState, useEffect } from 'react';
import { Activity, Radio, Cpu, Wifi, ShieldCheck, MapPin } from 'lucide-react';
import { motion } from 'framer-motion';

function App() {
  const [telemetry, setTelemetry] = useState({
    online: false,
    trustScore: 0,
    centerHz: 80000000,
    uplink: 'DISCONNECTED',
    magUt: 0,
  });

  // Simulate auto-connection sequence and live telemetry flow
  useEffect(() => {
    let interval;
    const connect = async () => {
      // Simulate C2 handshake
      await new Promise(r => setTimeout(r, 1000));
      setTelemetry(prev => ({ ...prev, online: true, uplink: 'ESTABLISHING...' }));
      
      await new Promise(r => setTimeout(r, 1000));
      setTelemetry(prev => ({ ...prev, uplink: 'CONNECTED: ALPHA NODE', trustScore: 0.4 }));

      interval = setInterval(() => {
        setTelemetry(prev => ({
          ...prev,
          trustScore: Math.min(1.0, prev.trustScore + Math.random() * 0.05),
          magUt: 40 + Math.random() * 15,
          centerHz: 80000000 + (Math.random() - 0.5) * 1000,
        }));
      }, 1000);
    };
    
    connect();
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <header className="header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Activity color="var(--text-highlight)" size={28} />
          <h2>DSLV-ZPDI Mobile C2</h2>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <span className="text-accent">{telemetry.uplink}</span>
          <div className={`status-indicator ${telemetry.online ? 'status-active' : 'status-error'}`} />
        </div>
      </header>

      <main className="grid-layout">
        {/* Node Connectivity Panel */}
        <motion.div 
          className="glass-panel"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
            <Wifi color="var(--text-highlight)" />
            <h3>Node Uplink</h3>
          </div>
          <div className="metric-label">Target IPv4 (Alpha)</div>
          <div className="metric-value" style={{ fontSize: '1.5rem' }}>10.29.134.69</div>
          <div style={{ marginTop: '20px' }}>
            <div className="metric-label">Pipeline Connection</div>
            <div style={{ color: telemetry.online ? 'var(--text-highlight)' : 'var(--error-color)', fontWeight: 600, marginTop: '5px' }}>
              {telemetry.online ? 'WS:// ACTIVE (Port 8443)' : 'OFFLINE'}
            </div>
          </div>
        </motion.div>

        {/* SDR Telemetry Panel */}
        <motion.div 
          className="glass-panel"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
            <Radio color="var(--text-highlight)" />
            <h3>SDR Telemetry</h3>
          </div>
          <div className="metric-label">Tuned Center Frequency</div>
          <div className="metric-value">{(telemetry.centerHz / 1e6).toFixed(4)} <span style={{ fontSize: '1rem', color: 'var(--text-main)' }}>MHz</span></div>
          
          <div style={{ marginTop: '20px' }}>
            <div className="metric-label">Baseband Rx Power</div>
            <div className="progress-bar-bg">
              <div className="progress-bar-fill" style={{ width: `${Math.random() * 30 + 40}%` }} />
            </div>
          </div>
        </motion.div>

        {/* Hardware Status Panel */}
        <motion.div 
          className="glass-panel"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
            <Cpu color="var(--text-highlight)" />
            <h3>Sensor Array</h3>
          </div>
          <div className="metric-label">Magnetometer (μT)</div>
          <div className="metric-value">{telemetry.magUt.toFixed(2)}</div>
          
          <div style={{ marginTop: '20px' }}>
            <div className="metric-label">C2 Hardware Synchronization</div>
            <div style={{ color: 'var(--text-highlight)', fontWeight: 600, marginTop: '5px' }}>LOCKED & TRACKING</div>
          </div>
        </motion.div>

        {/* Trust Score Panel */}
        <motion.div 
          className="glass-panel"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
            <ShieldCheck color="var(--text-highlight)" />
            <h3>Trust Score</h3>
          </div>
          <div className="metric-value">{(telemetry.trustScore * 100).toFixed(1)}%</div>
          <div className="progress-bar-bg" style={{ height: '10px', borderRadius: '5px' }}>
            <div className="progress-bar-fill" style={{ width: `${telemetry.trustScore * 100}%` }} />
          </div>
          <div style={{ marginTop: '20px' }}>
            <button className="action-btn" onClick={() => alert('Forcing pipeline flush...')}>
              FORCE SYNC
            </button>
          </div>
        </motion.div>
      </main>
    </>
  );
}

export default App;
