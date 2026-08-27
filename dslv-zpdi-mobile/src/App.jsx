import React, { useState, useEffect, useRef } from 'react';
import { Activity, Radio, Cpu, Wifi, ShieldCheck, MapPin, Settings, Zap, List, Terminal, Lock, Unlock, PlayCircle, BarChart2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import './App.css';
import crestStamp from './assets/crest_stamp.jpg';
import galleonPlate from './assets/galleon_plate.jpg';

const SdrPresets = [
  { name: 'FM Broadcast', hz: 98100000 },
  { name: 'VHF Airband', hz: 120000000 },
  { name: 'Marine VHF', hz: 156800000 },
  { name: 'NOAA Wx', hz: 162400000 },
  { name: 'ADS-B', hz: 1090000000 },
  { name: 'AM Broadcast', hz: 1000000 },
];

function App() {
  const [activeTab, setActiveTab] = useState('ops');
  const [telemetry, setTelemetry] = useState({
    online: false,
    trustScore: 0.98,
    centerHz: 98100000,
    uplink: 'DISCONNECTED',
    magUt: 45.2,
    cpu: 32,
    ram: 45,
    radon: 1.2,
    sfi: 140,
    kp: 2,
    mode: 'WFM',
    locked: true
  });
  
  const [pin, setPin] = useState('');
  const [showPin, setShowPin] = useState(false);

  useEffect(() => {
    const wsProto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsHost = window.location.hostname || '10.42.0.1';
    const wsPort = import.meta.env.VITE_ZPDI_WS_PORT || '8000';
    let ws;
    try {
      ws = new WebSocket(`${wsProto}://${wsHost}:${wsPort}/ws/live`);
      let lastUpdateTime = 0;
      
      ws.onopen = () => {
        setTelemetry(prev => ({ ...prev, online: true, uplink: `LIVE: ${wsHost}:${wsPort}` }));
      };
      
      ws.onmessage = (event) => {
        try {
          const now = Date.now();
          if (now - lastUpdateTime < 100) return;
          lastUpdateTime = now;
          const data = JSON.parse(event.data);
          if (data.layer1) {
            setTelemetry(prev => ({
              ...prev,
              centerHz: data.layer1.center_frequency_hz || prev.centerHz,
              magUt: (data.layer3 && data.layer3.mag_ut) ? data.layer3.mag_ut : prev.magUt,
              trustScore: (data.layer3 && data.layer3.trust_score) ? data.layer3.trust_score : prev.trustScore,
              cpu: data.sys?.cpu || prev.cpu,
              ram: data.sys?.ram || prev.ram,
            }));
          }
        } catch (err) {}
      };
      
      ws.onclose = () => {
        setTelemetry(prev => ({ ...prev, online: false, uplink: 'SIMULATOR (OFFLINE)' }));
      };
    } catch (e) {
      setTelemetry(prev => ({ ...prev, online: false, uplink: 'SIMULATOR (OFFLINE)' }));
    }
    
    // Simulate waterfall data
    const interval = setInterval(() => {
      setTelemetry(prev => ({
        ...prev,
        cpu: prev.online ? prev.cpu : 20 + Math.random() * 15,
        magUt: prev.online ? prev.magUt : 45 + Math.random() * 2,
      }));
    }, 1000);
    
    return () => {
      if (ws) ws.close();
      clearInterval(interval);
    };
  }, []);

  const handlePinSubmit = (e) => {
    e.preventDefault();
    if (pin === '1988') {
      setTelemetry(prev => ({...prev, locked: false}));
      setShowPin(false);
      alert('MIMO TX / TDOA unsealed.');
    } else {
      alert('Invalid PIN');
    }
    setPin('');
  };

  const handleTune = (hz) => {
    setTelemetry(prev => ({...prev, centerHz: hz}));
    // In a real app, we would POST to /api/sdr/tune
  };

  const renderWaterfall = () => (
    <div className="waterfall-container" onClick={(e) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const pct = x / rect.width;
      const span = 2000000; // 2 MHz span
      const newFreq = telemetry.centerHz - (span/2) + (span * pct);
      handleTune(newFreq);
    }}>
      <div className="waterfall-grid"></div>
      <div className="waterfall-sweep"></div>
      <div className="waterfall-label">LIVE RF WATERFALL (TAP TO TUNE)</div>
    </div>
  );

  return (
    <div className="app-container">
      <header className="c2-header">
        <div className="header-title">
          <Activity color="var(--text-highlight)" size={24} />
          <h2>DynoGatorLabs DSLV-ZPDI</h2>
        </div>
        <div className="header-status">
          <span className="text-accent">{telemetry.uplink}</span>
          <div className={`status-indicator ${telemetry.online ? 'status-active' : 'status-sim'}`} />
        </div>
      </header>

      <nav className="c2-nav">
        {['ops', 'rf', 'link'].map(tab => (
          <button 
            key={tab} 
            className={`nav-tab ${activeTab === tab ? 'active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab.toUpperCase()}
          </button>
        ))}
      </nav>

      <main className="c2-content">
        <AnimatePresence mode="wait">
          {activeTab === 'ops' && (
            <motion.div key="ops" initial={{opacity:0, x:-20}} animate={{opacity:1, x:0}} exit={{opacity:0, x:20}} className="tab-pane">
              <div className="glass-panel main-panel">
                <div className="panel-header">
                  <Terminal size={18} />
                  <h3>Primary Pipeline</h3>
                  {telemetry.locked ? <Lock size={16} className="text-error ml-auto" /> : <Unlock size={16} className="text-highlight ml-auto" />}
                </div>
                {renderWaterfall()}
                <div className="metrics-grid mt-4">
                  <div className="metric-box">
                    <div className="metric-label">KCET-ATLAS Kuramoto</div>
                    <div className="metric-value">0.984 <span className="unit">γ</span></div>
                  </div>
                  <div className="metric-box">
                    <div className="metric-label">Alpha CPU / RAM</div>
                    <div className="metric-value">{telemetry.cpu.toFixed(0)}% / {telemetry.ram.toFixed(0)}%</div>
                  </div>
                  <div className="metric-box">
                    <div className="metric-label">Env: Radon / UPS</div>
                    <div className="metric-value">{telemetry.radon} <span className="unit">pCi/L</span> / OK</div>
                  </div>
                  <div className="metric-box">
                    <div className="metric-label">Space Wx (Kp / SFI)</div>
                    <div className="metric-value">{telemetry.kp} / {telemetry.sfi}</div>
                  </div>
                </div>
                <button className="action-btn w-full mt-4" onClick={() => alert('Session event sealed.')}>
                  <ShieldCheck size={16} style={{display:'inline', marginRight:'8px'}}/>
                  SEAL CAPTURE (WRITE SESSION)
                </button>
              </div>
            </motion.div>
          )}

          {activeTab === 'rf' && (
            <motion.div key="rf" initial={{opacity:0, x:-20}} animate={{opacity:1, x:0}} exit={{opacity:0, x:20}} className="tab-pane">
              <div className="glass-panel main-panel">
                <div className="panel-header">
                  <Radio size={18} />
                  <h3>PlutoSDR+ Control</h3>
                </div>
                <div className="freq-display">
                  {(telemetry.centerHz / 1e6).toFixed(4)} <span className="unit">MHz</span>
                </div>
                <div className="ctrl-group mt-4">
                  <button className="ctrl-btn active">SWEEP</button>
                  <button className="ctrl-btn">NARROW</button>
                  <button className="ctrl-btn">SCOPE</button>
                </div>
                <div className="ctrl-group mt-2">
                  <button className="ctrl-btn" onClick={() => setTelemetry(t => ({...t, mode: 'WFM'}))} style={{opacity: telemetry.mode==='WFM'?1:0.5}}>WFM</button>
                  <button className="ctrl-btn" onClick={() => setTelemetry(t => ({...t, mode: 'RAW'}))} style={{opacity: telemetry.mode==='RAW'?1:0.5}}>RAW</button>
                </div>
                
                <h4 className="sub-heading mt-6">Presets (Front Range Sim)</h4>
                <div className="presets-grid">
                  {SdrPresets.map(p => (
                    <button key={p.name} className="preset-btn" onClick={() => handleTune(p.hz)}>
                      <span className="preset-name">{p.name}</span>
                      <span className="preset-hz">{(p.hz/1e6).toFixed(1)}</span>
                    </button>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'link' && (
            <motion.div key="link" initial={{opacity:0, x:-20}} animate={{opacity:1, x:0}} exit={{opacity:0, x:20}} className="tab-pane">
              <div className="glass-panel main-panel">
                <div className="panel-header">
                  <Wifi size={18} />
                  <h3>Link Identity & Security</h3>
                </div>
                <div className="art-container mb-4">
                  <img src={galleonPlate} alt="Galleon Plate" className="galleon-art" />
                </div>
                
                {telemetry.locked ? (
                  <div className="pin-entry mt-4">
                    <div className="metric-label mb-2">OPERATOR PIN REQUIRED</div>
                    <form onSubmit={handlePinSubmit} className="flex gap-2">
                      <input 
                        type="password" 
                        value={pin} 
                        onChange={e => setPin(e.target.value)}
                        placeholder="----"
                        className="pin-input"
                        maxLength={4}
                      />
                      <button type="submit" className="action-btn">UNSEAL</button>
                    </form>
                    <p className="hint-text mt-2">Unseals MIMO TX / TDOA / Hop Monitor</p>
                  </div>
                ) : (
                  <div className="unsealed-controls mt-4">
                    <div className="metric-label text-highlight mb-2">SECURITY UNSEALED</div>
                    <div className="grid gap-2">
                      <button className="ctrl-btn text-left"><Zap size={14} className="inline mr-2"/> MIMO TX CONTROL</button>
                      <button className="ctrl-btn text-left"><MapPin size={14} className="inline mr-2"/> TDOA PLACEMENT</button>
                      <button className="ctrl-btn text-left"><BarChart2 size={14} className="inline mr-2"/> HOP MONITOR</button>
                    </div>
                  </div>
                )}
                
                <div className="art-container mt-6" style={{textAlign: 'center'}}>
                  <img src={crestStamp} alt="DynoGator Crest" className="crest-art" />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}

export default App;
