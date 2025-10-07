import { useState, useEffect } from 'react'
import './ConfigEditor.css'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8082'

function ConfigEditor() {
  const [config, setConfig] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [reloading, setReloading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [validationError, setValidationError] = useState<string | null>(null)

  // Load config on mount
  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${BACKEND_URL}/config`)
      if (!response.ok) {
        throw new Error(`Failed to load config: ${response.statusText}`)
      }

      const data = await response.json()
      setConfig(JSON.stringify(data, null, 2))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load configuration')
    } finally {
      setLoading(false)
    }
  }

  const validateJSON = (text: string): boolean => {
    try {
      JSON.parse(text)
      setValidationError(null)
      return true
    } catch (err) {
      setValidationError(err instanceof Error ? err.message : 'Invalid JSON')
      return false
    }
  }

  const handleSave = async () => {
    setError(null)
    setSuccess(null)

    // Validate JSON first
    if (!validateJSON(config)) {
      return
    }

    setSaving(true)

    try {
      const parsedConfig = JSON.parse(config)

      const response = await fetch(`${BACKEND_URL}/config`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(parsedConfig),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `Save failed: ${response.statusText}`)
      }

      const result = await response.json()
      setSuccess(result.message)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration')
    } finally {
      setSaving(false)
    }
  }

  const handleReload = async () => {
    setError(null)
    setSuccess(null)
    setReloading(true)

    try {
      const response = await fetch(`${BACKEND_URL}/config/reload`, {
        method: 'POST',
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `Reload failed: ${response.statusText}`)
      }

      const result = await response.json()
      setSuccess(result.message)

      // Reload the config from the server
      await loadConfig()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reload configuration')
    } finally {
      setReloading(false)
    }
  }

  const handleTextChange = (text: string) => {
    setConfig(text)
    // Clear validation error when user is typing
    setValidationError(null)
  }

  if (loading) {
    return (
      <div className="config-editor">
        <div className="loading">Loading configuration...</div>
      </div>
    )
  }

  return (
    <div className="config-editor">
      <div className="header">
        <h1>Configuration Editor</h1>
        <div className="actions">
          <button onClick={handleSave} disabled={saving || !!validationError} className="save-btn">
            {saving ? 'Saving...' : 'Save'}
          </button>
          <button onClick={handleReload} disabled={reloading} className="reload-btn">
            {reloading ? 'Reloading...' : 'Reload'}
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}
      {validationError && <div className="validation-error">JSON Error: {validationError}</div>}

      <textarea
        className="config-textarea"
        value={config}
        onChange={(e) => handleTextChange(e.target.value)}
        spellCheck={false}
      />

      <div className="help">
        <h3>Usage:</h3>
        <ol>
          <li>Edit the configuration JSON above</li>
          <li>Click <strong>Save</strong> to write changes to disk (validates JSON first)</li>
          <li>Click <strong>Reload</strong> to apply changes to the running application</li>
        </ol>
        <p><strong>Note:</strong> Configuration is automatically validated before saving.</p>
      </div>
    </div>
  )
}

export default ConfigEditor
