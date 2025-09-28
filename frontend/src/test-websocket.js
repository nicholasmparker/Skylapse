// Simple Socket.IO test
import { io } from 'socket.io-client';

const socket = io('http://localhost:8081', {
  autoConnect: false,
  forceNew: true,
  transports: ['polling', 'websocket']
});

socket.on('connect', () => {
  console.log('✅ Socket.IO connected:', socket.id);
});

socket.on('disconnect', () => {
  console.log('❌ Socket.IO disconnected');
});

socket.on('connect_error', (error) => {
  console.log('💥 Socket.IO connection error:', error);
});

console.log('🔌 Attempting to connect...');
socket.connect();

setTimeout(() => {
  console.log('📊 Connection status:', {
    connected: socket.connected,
    disconnected: socket.disconnected,
    id: socket.id
  });
}, 5000);
