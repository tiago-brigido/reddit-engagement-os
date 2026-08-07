chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "indexConversation") {
    fetch('http://localhost:8000/conversations/index', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(request.data)
    })
    .then(r => r.json())
    .then(data => sendResponse({status: 'indexed', id: data.id}))
    .catch(err => sendResponse({error: err.message}));
    return true;
  }
  
  if (request.action === "generateResponse") {
    fetch('http://localhost:8000/responses/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        post_content: request.content,
        subreddit: request.subreddit,
        model: 'laguna-s-2.1-free'
      })
    })
    .then(r => r.json())
    .then(data => sendResponse({suggestions: data}))
    .catch(err => sendResponse({error: err.message}));
    return true;
  }
});

chrome.runtime.onInstalled.addListener(() => {
  console.log('Reddit Engagement OS extension installed');
});
