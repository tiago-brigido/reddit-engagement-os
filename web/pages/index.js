import { useState, useEffect } from 'react'
import axios from 'axios'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts'

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedTab, setSelectedTab] = useState('dashboard')
  
  useEffect(() => {
    fetchMetrics()
  }, [])
  
  async function fetchMetrics() {
    try {
      const res = await axios.get('http://localhost:8000/metrics/dashboard')
      setMetrics(res.data)
      setLoading(false)
    } catch (err) {
      console.error(err)
      setLoading(false)
    }
  }
  
  const tabs = ['Dashboard', 'Responses', 'Topics', 'Index Post']
  
  return (
    <div className="min-h-screen bg-dark text-white p-6">
      <div className="max-w-6xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Reddit Engagement OS</h1>
          <p className="text-gray-300">Your second brain for Reddit engagement</p>
        </header>
        
        <nav className="flex gap-4 mb-6">
          {tabs.map(tab => (
            <button
              key={tab}
              onClick={() => setSelectedTab(tab.toLowerCase())}
              className={`px-4 py-2 rounded-lg transition-all ${
                selectedTab === tab.toLowerCase() 
                  ? 'bg-primary text-white' 
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {tab}
            </button>
          ))}
        </nav>
        
        {selectedTab === 'dashboard' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-gray-800 p-6 rounded-xl">
              <h3 className="text-gray-400 text-sm">Total Conversations</h3>
              <p className="text-3xl font-bold text-primary">{metrics?.total_conversations || 0}</p>
            </div>
            <div className="bg-gray-800 p-6 rounded-xl">
              <h3 className="text-gray-400 text-sm">Saved Responses</h3>
              <p className="text-3xl font-bold text-primary">{metrics?.total_responses || 0}</p>
            </div>
            <div className="bg-gray-800 p-6 rounded-xl">
              <h3 className="text-gray-400 text-sm">Karma Events</h3>
              <p className="text-3xl font-bold text-primary">{metrics?.total_karma_events || 0}</p>
            </div>
          </div>
        )}
        
        {selectedTab === 'index post' && (
          <div className="bg-gray-800 p-6 rounded-xl">
            <h2 className="text-xl mb-4">Index Reddit Post</h2>
            <div className="space-y-4">
              <div>
                <label className="block mb-2">Post URL / Content</label>
                <textarea 
                  className="w-full bg-gray-900 p-3 rounded-lg"
                  rows="4"
                  placeholder="https://reddit.com/r/..."
                />
              </div>
              <button className="bg-primary hover:bg-blue-600 px-4 py-2 rounded-lg">
                Index for Analysis
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export async function getServerSideProps() {
  return { props: {} }
}
