/**
 * Minimal Schedule Component - Absolute minimal test
 */

import React from 'react';

export const MinimalSchedule: React.FC = () => {
  console.log('🔥 MinimalSchedule: Rendering');

  return (
    <div style={{ padding: '20px', backgroundColor: '#f0f9ff', border: '2px solid #0ea5e9' }}>
      <h1 style={{ color: '#0c4a6e', fontSize: '24px', fontWeight: 'bold' }}>
        Minimal Schedule Test
      </h1>
      <p style={{ color: '#075985', marginTop: '10px' }}>
        This component uses zero external dependencies.
      </p>
      <div style={{ marginTop: '20px', padding: '10px', backgroundColor: '#e0f2fe', borderRadius: '4px' }}>
        <strong>Status:</strong> Component rendered successfully without any CSS classes or hooks.
      </div>
    </div>
  );
};

export default MinimalSchedule;
