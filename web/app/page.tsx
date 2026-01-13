'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts'

interface PriceData {
  spx: number | null
  es: number | null
  spread: number | null
  timestamp: string
}

interface GammaData {
  spx_price: number
  es_price: number
  spread: number
  regime: string
  levels_spx: { [key: string]: number }
  levels_es: { [key: string]: number }
  gamma_profile: Array<{
    strike: number
    net_gamma: number
    call_gamma: number
    put_gamma: number
  }>
  timestamp: string
}

export default function Home() {
  const [prices, setPrices] = useState<PriceData | null>(null)
  const [gamma, setGamma] = useState<GammaData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch prices and gamma data
      const [pricesRes, gammaRes] = await Promise.all([
        axios.get('/api/prices'),
        axios.get('/api/gamma')
      ])

      if (pricesRes.data.success) {
        setPrices(pricesRes.data.data)
      }

      if (gammaRes.data.success) {
        console.log('Gamma data received:', gammaRes.data.data)
        console.log('PUT WALL ES:', gammaRes.data.data.levels_es?.put_wall)
        console.log('CALL WALL ES:', gammaRes.data.data.levels_es?.call_wall)
        console.log('ES PRICE:', gammaRes.data.data.es_price)
        setGamma(gammaRes.data.data)
      }

      setLoading(false)
    } catch (err: any) {
      setError(err.message || 'Failed to fetch data')
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()

    if (autoRefresh) {
      const interval = setInterval(fetchData, 30000) // 30 seconds
      return () => clearInterval(interval)
    }
  }, [autoRefresh])

  const formatCurrency = (value: number | null) => {
    if (value === null) return 'N/A'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value)
  }

  const getRegimeColor = (regime: string) => {
    if (regime === 'long_gamma') return 'bg-green-500'
    if (regime === 'short_gamma') return 'bg-red-500'
    return 'bg-gray-500'
  }

  const getRegimeText = (regime: string) => {
    if (regime === 'long_gamma') return 'LONG GAMMA - Mean Reversion Expected'
    if (regime === 'short_gamma') return 'SHORT GAMMA - Higher Volatility Expected'
    return 'NEUTRAL'
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white p-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold mb-2">📊 GammaOption</h1>
            <p className="text-gray-400">SPX 0DTE Gamma Analysis - ES Futures Levels</p>
          </div>
          <div className="flex gap-4">
            <button
              onClick={fetchData}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50 transition"
            >
              {loading ? '🔄 Loading...' : '🔄 Refresh'}
            </button>
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-4 py-2 rounded-lg transition ${
                autoRefresh ? 'bg-green-600 hover:bg-green-700' : 'bg-gray-600 hover:bg-gray-700'
              }`}
            >
              {autoRefresh ? '✓ Auto-refresh ON' : '✗ Auto-refresh OFF'}
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-500/20 border border-red-500 rounded-lg p-4 mb-6">
            <p className="text-red-200">⚠️ Error: {error}</p>
          </div>
        )}

        {/* Price Cards */}
        {prices && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
              <div className="text-gray-400 text-sm mb-2">SPX Cash</div>
              <div className="text-3xl font-bold">{formatCurrency(prices.spx)}</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
              <div className="text-gray-400 text-sm mb-2">ES Futures</div>
              <div className="text-3xl font-bold">{formatCurrency(prices.es)}</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
              <div className="text-gray-400 text-sm mb-2">ES-SPX Spread</div>
              <div className={`text-3xl font-bold ${prices.spread && prices.spread > 0 ? 'text-green-400' : 'text-red-400'}`}>
                {prices.spread ? (prices.spread > 0 ? '+' : '') + prices.spread.toFixed(2) : 'N/A'}
              </div>
            </div>
          </div>
        )}

        {/* Regime */}
        {gamma && (
          <div className={`${getRegimeColor(gamma.regime)} rounded-lg p-6 mb-6 text-center`}>
            <div className="text-2xl font-bold">
              {getRegimeText(gamma.regime)}
            </div>
          </div>
        )}

        {/* Key Levels */}
        {gamma && (
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 mb-6">
            <h2 className="text-2xl font-bold mb-4">🎯 Key Gamma Levels (ES Futures)</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {gamma.levels_es.put_wall && (
                <div className="bg-green-500/20 border border-green-500 rounded-lg p-4">
                  <div className="text-green-400 font-semibold mb-1">Put Wall (Support)</div>
                  <div className="text-2xl font-bold">{formatCurrency(gamma.levels_es.put_wall)}</div>
                  <div className="text-sm text-gray-400 mt-1">
                    SPX: {formatCurrency(gamma.levels_spx.put_wall)}
                  </div>
                  {gamma.es_price && (
                    <div className="text-sm mt-2">
                      Distance: {(gamma.es_price - gamma.levels_es.put_wall).toFixed(2)} pts
                    </div>
                  )}
                </div>
              )}
              {gamma.levels_es.gamma_flip && (
                <div className="bg-blue-500/20 border border-blue-500 rounded-lg p-4">
                  <div className="text-blue-400 font-semibold mb-1">Gamma Flip (Pivot)</div>
                  <div className="text-2xl font-bold">{formatCurrency(gamma.levels_es.gamma_flip)}</div>
                  <div className="text-sm text-gray-400 mt-1">
                    SPX: {formatCurrency(gamma.levels_spx.gamma_flip)}
                  </div>
                  {gamma.es_price && (
                    <div className="text-sm mt-2">
                      Distance: {(gamma.es_price - gamma.levels_es.gamma_flip).toFixed(2)} pts
                    </div>
                  )}
                </div>
              )}
              {gamma.levels_es.call_wall && (
                <div className="bg-red-500/20 border border-red-500 rounded-lg p-4">
                  <div className="text-red-400 font-semibold mb-1">Call Wall (Resistance)</div>
                  <div className="text-2xl font-bold">{formatCurrency(gamma.levels_es.call_wall)}</div>
                  <div className="text-sm text-gray-400 mt-1">
                    SPX: {formatCurrency(gamma.levels_spx.call_wall)}
                  </div>
                  {gamma.es_price && (
                    <div className="text-sm mt-2">
                      Distance: {(gamma.levels_es.call_wall - gamma.es_price).toFixed(2)} pts
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Gamma Profile Chart */}
        {gamma && gamma.gamma_profile && (
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 mb-6">
            <h2 className="text-2xl font-bold mb-4">📈 Gamma Exposure Profile</h2>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={gamma.gamma_profile}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="strike" 
                    stroke="#9CA3AF"
                    tickFormatter={(value) => `$${value.toFixed(0)}`}
                  />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                    labelFormatter={(value) => `Strike: $${value}`}
                  />
                  <Legend />
                  <ReferenceLine 
                    x={gamma.spx_price} 
                    stroke="#EF4444" 
                    strokeDasharray="5 5"
                    label={{ value: 'Current SPX', fill: '#EF4444', position: 'top' }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="net_gamma" 
                    stroke="#3B82F6" 
                    name="Net Gamma"
                    dot={false}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="call_gamma" 
                    stroke="#EF4444" 
                    name="Call Gamma"
                    dot={false}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="put_gamma" 
                    stroke="#10B981" 
                    name="Put Gamma"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="text-center text-gray-500 text-sm mt-8">
          <p>Last updated: {prices?.timestamp ? new Date(prices.timestamp).toLocaleString() : 'N/A'}</p>
          <p className="mt-2">⚠️ Testing mode with mock data. For production use, connect Polygon.io API.</p>
        </div>
      </div>
    </main>
  )
}
