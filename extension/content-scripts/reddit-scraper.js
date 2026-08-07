(function() {
  'use strict';
  
  function getCurrentPost() {
    const titleEl = document.querySelector('h1._eYtD20Xwwq9Rsl06QKC_') || 
                    document.querySelector('h1[data-testid="post-heading"]') ||
                    document.querySelector('.Post__title');
    
    const contentEl = document.querySelector('._d3ye1NExT4V9xqerBRmb') ||
                      document.querySelector('.Post__body') ||
                      document.querySelector('.md');
    
    const subredditEl = document.querySelector('.OMnrSnnHxBdAFjsAx9QG') ||
                        document.querySelector('.dataWAYASubreddit');
    
    const url = window.location.href;
    const redditIdMatch = url.match(/\/comments\/(\w+)/);
    const redditId = redditIdMatch ? redditIdMatch[1] : '';
    const subredditMatch = url.match(/r\/(\w+)/) || (subredditEl && subredditEl.textContent);
    const subreddit = subredditMatch ? subredditMatch.replace('r/', '') : '';
    
    return {
      reddit_id: redditId,
      subreddit: subreddit,
      title: titleEl ? titleEl.textContent : '',
      post_url: url,
      content: contentEl ? contentEl.textContent.slice(0, 3000) : '',
      author: '',
      score: 0,
      num_comments: 0,
      created_utc: new Date().toISOString(),
      permalink: url
    };
  }
  
  function sendToIndexer(data) {
    chrome.runtime.sendMessage({
      action: "indexConversation",
      data: data
    });
  }
  
  function injectCaptureButton() {
    const target = document.querySelector('#app-root');
    if (!target) return;
    
    if (document.getElementById('engagement-os-capture')) return;
    
    const btn = document.createElement('button');
    btn.id = 'engagement-os-capture';
    btn.textContent = '🧠 Index for Analysis';
    btn.style.cssText = `
      position: fixed;
      top: 80px;
      right: 20px;
      z-index: 9999;
      background: #0079d3;
      color: white;
      border: none;
      padding: 8px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: bold;
    `;
    
    btn.addEventListener('click', () => {
      const postData = getCurrentPost();
      sendToIndexer(postData);
      btn.textContent = '✅ Indexed!';
      setTimeout(() => btn.textContent = '🧠 Index for Analysis', 2000);
    });
    
    target.appendChild(btn);
  }
  
  const observer = new MutationObserver(() => {
    if (window.location.pathname.includes('/comments/')) {
      injectCaptureButton();
    }
  });
  
  observer.observe(document.body, { childList: true, subtree: true });
  
  injectCaptureButton();
})();
