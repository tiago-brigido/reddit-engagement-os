document.addEventListener('DOMContentLoaded', function() {
  const API_URL = 'http://localhost:8000';
  
  async function fetchAPI(endpoint, options = {}) {
    const response = await fetch(`${API_URL}${endpoint}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options
    });
    return response.json();
  }
  
  async function loadMetrics() {
    try {
      const data = await fetchAPI('/metrics/dashboard');
      const container = document.getElementById('metrics-container');
      container.innerHTML = `
        <div class="metric-card">Conversations: ${data.total_conversations}</div>
        <div class="metric-card">Responses: ${data.total_responses}</div>
        <div class="metric-card">Karma Events: ${data.total_karma_events}</div>
      `;
    } catch (err) {
      console.error('Failed to load metrics:', err);
    }
  }
  
  document.getElementById('index-btn').addEventListener('click', function() {
    showSection('index-section');
  });
  document.getElementById('generate-btn').addEventListener('click', function() {
    showSection('generate-section');
  });
  document.getElementById('dashboard-btn').addEventListener('click', function() {
    showSection('dashboard-section');
    loadMetrics();
  });
  
  function showSection(id) {
    document.querySelectorAll('section').forEach(s => s.style.display = 'none');
    document.getElementById(id).style.display = 'block';
    document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
    document.querySelector(`#${id.replace('-section','')}`).classList.add('active');
  }
  
  document.getElementById('generate-btn-action').addEventListener('click', async function() {
    const content = document.getElementById('post-content').value;
    const subreddit = document.getElementById('subreddit').value;
    
    if (!content || !subreddit) {
      alert('Please fill in all fields');
      return;
    }
    
    const output = document.getElementById('suggestions-output');
    output.innerHTML = '<p>Generating suggestions...</p>';
    
    try {
      const data = await fetchAPI('/responses/generate', {
        method: 'POST',
        body: JSON.stringify({ post_content: content, subreddit: subreddit })
      });
      
      output.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
    } catch (err) {
      output.innerHTML = `<p style="color:red">Error: ${err.message}</p>`;
    }
  });
  
  loadMetrics();
});
