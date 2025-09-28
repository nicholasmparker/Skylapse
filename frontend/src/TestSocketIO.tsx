import React, { useEffect, useState } from 'react';
import { io, Socket } from 'socket.io-client';

export default function TestSocketIO() {
  const [status, setStatus] = useState('Disconnected');
  const [socket, setSocket] = useState<Socket | null>(null);
  const [logs, setLogs] = useState<string[]>([]);

  const log = (message: string) => {
    console.log(message);
    setLogs(prev => [...prev.slice(-10), `${new Date().toLocaleTimeString()}: ${message}`]);
  };

  useEffect(() => {
    log('Creating Socket.IO connection...');

    const newSocket = io('http://localhost:8081', {
      autoConnect: false,
      forceNew: true,
      transports: ['polling', 'websocket'],
      auth: { token: 'dev-token-for-websocket-connection' },
      query: { token: 'dev-token-for-websocket-connection' }
    });

    newSocket.on('connect', () => {
      log(`✅ Connected with ID: ${newSocket.id}`);
      setStatus('Connected');
    });

    newSocket.on('disconnect', (reason) => {
      log(`❌ Disconnected: ${reason}`);
      setStatus('Disconnected');
    });

    newSocket.on('connect_error', (error) => {
      log(`💥 Connection error: ${error.message}`);
      setStatus('Error');
    });

    log('Attempting to connect...');
    newSocket.connect();
    setSocket(newSocket);

    return () => {
      log('Cleaning up socket...');
      newSocket.disconnect();
    };
  }, []);

  const manualConnect = () => {
    if (socket && !socket.connected) {
      log('Manual connect attempt...');
      socket.connect();
    }
  };

  const manualDisconnect = () => {
    if (socket && socket.connected) {
      log('Manual disconnect...');
      socket.disconnect();
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h1>Socket.IO Test Page</h1>

      <div style={{ marginBottom: '20px' }}>
        <strong>Status: </strong>
        <span style={{
          color: status === 'Connected' ? 'green' : status === 'Error' ? 'red' : 'orange'
        }}>
          {status}
        </span>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <button onClick={manualConnect} disabled={socket?.connected}>
          Connect
        </button>
        <button onClick={manualDisconnect} disabled={!socket?.connected} style={{ marginLeft: '10px' }}>
          Disconnect
        </button>
      </div>

      <div>
        <h3>Connection Details:</h3>
        <div>Socket ID: {socket?.id || 'N/A'}</div>
        <div>Connected: {socket?.connected ? 'Yes' : 'No'}</div>
        <div>Disconnected: {socket?.disconnected ? 'Yes' : 'No'}</div>
        <div>Transport: {(socket as any)?.io?.engine?.transport?.name || 'N/A'}</div>
      </div>

      <div style={{ marginTop: '20px' }}>
        <h3>Logs:</h3>
        <div style={{
          height: '200px',
          overflow: 'auto',
          border: '1px solid #ccc',
          padding: '10px',
          backgroundColor: '#f5f5f5'
        }}>
          {logs.map((log, i) => (
            <div key={i}>{log}</div>
          ))}
        </div>
      </div>
    </div>
  );
}
