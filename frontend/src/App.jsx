import { useEffect, useRef, useState } from 'react';
import {
  ArrowLeft, ArrowRight, ArrowUp, BarChart3, Bot, Check, CheckCircle2, ChevronDown, CircleHelp, Eye, EyeOff, FileText, FolderOpen,
  Github, HelpCircle, LayoutDashboard, LockKeyhole, Mail, Menu, MoreHorizontal, Paperclip,
  Plus, Search, Settings, ShieldCheck, Sparkles, Trash2, UserRound, X
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/context/AuthContext';
import { client } from '@/lib/langgraph-client';
import { processPDF } from '@/lib/pdf';
import { retrievalAssistantStreamConfig, indexConfig } from '@/constants/graphConfigs';
import { supabase } from "./lib/supabase";

function getInitials(name) {
  if (!name) return '?';
  return name
    .trim()
    .split(/\s+/)
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();
}

export default function App() {
  const { toast } = useToast();
  const { user, isAuthenticated, isLoading, login, signup } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [files, setFiles] = useState([]);
  const [isThinking, setIsThinking] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [route, setRoute] = useState(() => window.location.hash.slice(1) || 'assistant');
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef(null);
  const threadIdRef = useRef(null);

  /** Creates a chat thread on first use and reuses it for the rest of the conversation. */
  const ensureThread = async () => {
    if (threadIdRef.current) return threadIdRef.current;
    const thread = await client.createThread({ kind: 'chat' });
    threadIdRef.current = thread.thread_id;
    return thread.thread_id;
  };

  useEffect(() => {
    const syncRoute = () => setRoute(window.location.hash.slice(1) || 'assistant');
    window.addEventListener('hashchange', syncRoute);
    return () => window.removeEventListener('hashchange', syncRoute);
  }, []);

  const navigate = (nextRoute) => {
    window.location.hash = nextRoute;
    setSidebarOpen(false);
  };
  const notify = (title, description) => toast({ title, description });

  // Route protection: bounce signed-out users to /login, and signed-in
  // users away from /login and /signup.
  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated && route !== 'login' && route !== 'signup') {
      navigate('login');
    } else if (isAuthenticated && (route === 'login' || route === 'signup')) {
      navigate('assistant');
    }
  }, [isAuthenticated, isLoading, route]);

  if (isLoading) {
    return (
      <div className="auth-loading">
        <Sparkles size={20} />
        <span>Loading your workspace…</span>
      </div>
    );
  }

  if (route === 'login' || route === 'signup') {
    return (
      <AuthScreen
        mode={route}
        navigate={navigate}
        notify={notify}
        login={login}
        signup={signup}
      />
    );
  }

  if (!isAuthenticated) {
    // Redirect effect above will kick in; render nothing in the meantime.
    return null;
  }

  const sendMessage = async (event) => {
    event?.preventDefault();
    const question = input.trim();
    if (!question || isThinking) return;
    setMessages((all) => [...all, { role: 'user', content: question, time: 'Now' }]);
    setInput('');
    setIsThinking(true);

    try {
      const threadId = await ensureThread();
      const stream = client.client.runs.stream(threadId, 'retrieval_graph', {
        input: { query: question },
        config: { configurable: retrievalAssistantStreamConfig },
        streamMode: 'values',
      });

      let latestState = null;
      for await (const chunk of stream) {
        if (chunk.event === 'error') {
          throw new Error(chunk.data?.message || 'The assistant ran into an error.');
        }
        if (chunk.event === 'values') {
          latestState = chunk.data;
        }
      }

      const aiMessages = (latestState?.messages || []).filter(
        (m) => m.type === 'ai' || m.role === 'assistant',
      );
      const answer = aiMessages[aiMessages.length - 1]?.content || "I couldn't find an answer to that.";

      const seen = new Set();
      const sources = [];
      for (const doc of latestState?.documents || []) {
        const name = doc.metadata?.filename || doc.metadata?.source || 'Document';
        const page = doc.metadata?.loc?.pageNumber;
        const label = page ? `${name} · p. ${page}` : name;
        if (!seen.has(label)) {
          seen.add(label);
          sources.push(label);
        }
      }

      setMessages((all) => [
        ...all,
        { role: 'assistant', time: 'Now', content: answer, sources: sources.length ? sources : undefined },
      ]);
    } catch (error) {
      setMessages((all) => [
        ...all,
        { role: 'assistant', time: 'Now', content: `Something went wrong: ${error.message}` },
      ]);
      notify('Request failed', error.message);
    } finally {
      setIsThinking(false);
    }
  };

  const upload = async (event) => {
    const uploaded = Array.from(event.target.files || []);
    if (!uploaded.length) return;
    event.target.value = '';
    setIsUploading(true);

    for (const file of uploaded) {
      try {
        const docs = await processPDF(file);
        if (!docs.length) {
          notify('Empty document', `${file.name} has no extractable text.`);
          continue;
        }

        const thread = await client.createThread({ kind: 'ingestion', filename: file.name });
        await client.client.runs.wait(thread.thread_id, 'ingestion_graph', {
          input: { docs },
          config: { configurable: indexConfig },
        });

        setFiles((all) => [
          [file.name.replace(/\.pdf$/i, ''), `${docs.length} page${docs.length > 1 ? 's' : ''}`, 'Just now', 'PDF'],
          ...all,
        ]);
        notify('Document indexed', `${file.name} is ready to search.`);
      } catch (error) {
        notify('Upload failed', `${file.name}: ${error.message}`);
      }
    }

    setIsUploading(false);
  };

  const removeDocument = (documentName) => {
    setFiles((all) => all.filter(([name]) => name !== documentName));
    notify('Document removed', `${documentName} was removed from this workspace.`);
  };

  return <div className="app-shell">
    <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
      <button className="brand" onClick={() => navigate('assistant')} aria-label="Go to assistant"><div className="brand-mark"><Sparkles size={17}/></div><span>paperwise</span><span className="mobile-close" onClick={(event) => { event.stopPropagation(); setSidebarOpen(false); }}><X size={18}/></span></button>
      <button className="new-chat" onClick={() => { setMessages([]); threadIdRef.current = null; navigate('assistant'); notify('New conversation', 'Your conversation is ready.'); }}><Plus size={17}/>New conversation <span>⌘ K</span></button>
      <nav><p>WORKSPACE</p><NavItem active={route === 'assistant'} onClick={() => navigate('assistant')} icon={<Bot size={18}/>} label="Assistant"/><NavItem active={route === 'library'} onClick={() => navigate('library')} icon={<FolderOpen size={18}/>} label="Library" count={files.length}/><NavItem active={route === 'insights'} onClick={() => navigate('insights')} icon={<BarChart3 size={18}/>} label="Insights"/></nav>
      <div className="sidebar-bottom"><nav><NavItem active={route === 'help'} onClick={() => navigate('help')} icon={<HelpCircle size={18}/>} label="Help center"/><NavItem active={route === 'settings'} onClick={() => navigate('settings')} icon={<Settings size={18}/>} label="Settings"/></nav><button className="profile" onClick={() => navigate('settings')}><div className="avatar">{getInitials(user?.name)}</div><div><strong>{user?.name}</strong><small>Research workspace</small></div><MoreHorizontal size={18}/></button></div>
    </aside>
    {sidebarOpen && <div className="scrim" onClick={() => setSidebarOpen(false)}/>}
    <main className="main-area">
      <header className="topbar"><button className="menu-button" onClick={() => setSidebarOpen(true)} aria-label="Open navigation"><Menu size={21}/></button><button className="crumb" onClick={() => navigate('assistant')}><span>Research workspace</span><span>/</span><strong>{routeLabel(route)}</strong><ChevronDown size={15}/></button><div className="top-actions"><button className="icon-btn" onClick={() => setSearchOpen(true)} aria-label="Search documents"><Search size={19}/></button><button className="upgrade" onClick={() => navigate('upgrade')}><Sparkles size={15}/>Upgrade</button><button className="avatar small" onClick={() => navigate('settings')} aria-label="Open account settings">{getInitials(user?.name)}</button></div></header>
      {route === 'assistant' ? <section className="workspace">
        <div className="chat-panel">
          <div className="chat-heading"><div><p className="eyebrow">AI RESEARCH ASSISTANT</p><h1>Good morning{user?.name ? `, ${user.name.split(' ')[0]}` : ''}.</h1><p>Ask anything across your document library.</p></div><div className="status"><i></i>Library synced</div></div>
          <div className="suggestions"><button onClick={() => setInput('Summarize the key themes across my documents')}>Summarize key themes <ArrowUp size={15}/></button><button onClick={() => setInput('What information is missing from my research?')}>Find knowledge gaps <ArrowUp size={15}/></button><button onClick={() => setInput('Compare the risks raised in each document')}>Compare documents <ArrowUp size={15}/></button></div>
          <div className="messages">{messages.length === 0 ? <div className="empty-chat"><Sparkles/><h2>A fresh conversation</h2><p>Ask a question about your library to start researching.</p></div> : messages.map((message, index) => <Message key={index} message={message}/>) }{isThinking && <div className="thinking"><div className="assistant-badge"><Sparkles size={14}/></div><span></span><span></span><span></span></div>}</div>
          <form className="composer" onSubmit={sendMessage}><input ref={fileInputRef} type="file" accept="application/pdf" multiple onChange={upload} hidden/><button type="button" className="attach" disabled={isUploading} onClick={() => fileInputRef.current?.click()}><Paperclip size={19}/></button><input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask anything about your documents…"/><button className="send" disabled={!input.trim() || isThinking}><ArrowUp size={18}/></button><div className="composer-note">Paperwise can make mistakes. Check important info.</div></form>
        </div>
        <aside className="library-panel"><div className="library-head"><div><p className="eyebrow">KNOWLEDGE BASE</p><h2>Your library</h2></div><button onClick={() => fileInputRef.current?.click()}><Plus size={17}/>Add</button></div><div className="library-stat"><div className="stat-icon"><FileText size={19}/></div><div><strong>{files.length} documents</strong><p>Ready for retrieval</p></div><Check size={16}/></div><div className="doc-list">{files.slice(0, 5).map(([name, pages, date, initials], index) => <div className="doc" key={`${name}-${index}`}><div className="doc-icon">{initials}</div><div><strong>{name}</strong><p>{pages} · {date}</p></div><button onClick={() => navigate('library')} aria-label={`Open ${name}`}><MoreHorizontal size={18}/></button></div>)}</div><button className="view-library" onClick={() => navigate('library')}><LayoutDashboard size={16}/>View all documents</button><div className="tip"><div><Sparkles size={16}/></div><p><strong>Pro tip</strong>Upload reports, research, or meeting notes. Your assistant will cite each answer.</p></div></aside>
      </section> : <WorkspacePage route={route} files={files} navigate={navigate} upload={() => fileInputRef.current?.click()} removeDocument={removeDocument} notify={notify}/>} 
    </main>
    {searchOpen && <SearchDialog files={files} query={searchQuery} setQuery={setSearchQuery} close={() => setSearchOpen(false)} navigate={navigate}/>} 
  </div>;
}

function NavItem({ active, onClick, icon, label, count }) { return <button className={active ? 'active' : ''} onClick={onClick}>{icon}{label}{count !== undefined && <b>{count}</b>}</button>; }

function WorkspacePage({ route, files, navigate, upload, removeDocument, notify }) {
  const { user, logout } = useAuth();
  if (route === 'library') return <section className="page"><PageTitle eyebrow="KNOWLEDGE BASE" title="Your document library" description="Everything your assistant can search, reason over, and cite." action={<button className="primary-action" onClick={upload}><Plus size={17}/>Upload documents</button>}/><div className="document-grid">{files.map(([name, pages, date, initials]) => <article className="document-card" key={name}><div className="doc-icon big">{initials}</div><button className="remove-doc" onClick={() => removeDocument(name)} aria-label={`Remove ${name}`}><Trash2 size={16}/></button><h3>{name}</h3><p>{pages} · Uploaded {date}</p><button className="text-action" onClick={() => { navigate('assistant'); notify('Document selected', `Ask a question about ${name}.`); }}>Ask about this document <ArrowUp size={15}/></button></article>)}</div></section>;
  if (route === 'insights') return <section className="page"><PageTitle eyebrow="LIBRARY ANALYTICS" title="Research insights" description="A living overview of the knowledge in your workspace."/><div className="metrics"><Metric value={files.length} label="Indexed documents"/><Metric value="91" label="Searchable pages"/><Metric value="18" label="Linked themes"/></div><div className="insight-card"><BarChart3/><div><h3>Library coverage is strong</h3><p>Your documents span strategy, research, risk, and market planning. Ask the assistant to identify gaps before your next decision.</p><button className="text-action" onClick={() => { navigate('assistant'); }}>Find knowledge gaps <ArrowUp size={15}/></button></div></div></section>;
  if (route === 'settings') return <section className="page"><PageTitle eyebrow="WORKSPACE" title="Settings" description="Manage your Paperwise workspace and preferences."/><div className="settings-card"><UserRound/><div><h3>{user?.name}</h3><p>{user?.email} · Free plan</p></div><button className="secondary-action" onClick={() => navigate('upgrade')}>Manage plan</button></div><div className="settings-card"><Settings/><div><h3>Answer preferences</h3><p>Responses include document citations automatically.</p></div><button className="secondary-action" onClick={() => notify('Preferences saved', 'Citations will remain enabled for every answer.')}>Save preferences</button></div><div className="settings-card"><LockKeyhole/><div><h3>Session</h3><p>Switch accounts or securely sign out of this workspace.</p></div><button className="secondary-action" onClick={() => { logout(); navigate('login'); }}>Sign out</button></div></section>;
  if (route === 'help') return <section className="page"><PageTitle eyebrow="SUPPORT" title="Help center" description="Learn how to get the most from your document workspace."/><div className="help-list"><button onClick={() => navigate('library')}><FileText/>How to upload and manage documents <ArrowUp size={16}/></button><button onClick={() => navigate('assistant')}><Bot/>How citations work <ArrowUp size={16}/></button><button onClick={() => notify('Support request created', 'We will respond through your workspace email.') }><CircleHelp/>Contact support <ArrowUp size={16}/></button></div></section>;
  return <section className="page"><PageTitle eyebrow="PAPERWISE PRO" title="Go deeper with your research" description="Unlock more documents, team workspaces, and advanced research insights." action={<button className="primary-action" onClick={() => notify('Upgrade request received', 'Your account manager will help you choose a plan.')}>Choose a plan</button>}/><div className="upgrade-card"><Sparkles/><h3>Expand your knowledge base</h3><p>Build a richer, more connected research workspace with Paperwise Pro.</p><button className="secondary-action" onClick={() => navigate('assistant')}>Back to assistant <ArrowLeft size={15}/></button></div></section>;
}

function PageTitle({ eyebrow, title, description, action }) { return <div className="page-title"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p>{description}</p></div>{action}</div>; }
function Metric({ value, label }) { return <div className="metric"><strong>{value}</strong><span>{label}</span></div>; }
function SearchDialog({ files, query, setQuery, close, navigate }) { const matches = files.filter(([name]) => name.toLowerCase().includes(query.toLowerCase())); return <div className="dialog-backdrop" onClick={close}><section className="search-dialog" onClick={(event) => event.stopPropagation()}><div><Search size={18}/><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search your documents"/><button onClick={close}><X size={17}/></button></div><p>DOCUMENTS</p>{matches.length ? matches.map(([name, pages]) => <button key={name} onClick={() => { close(); navigate('library'); }}><FileText/><span>{name}<small>{pages}</small></span><ArrowUp size={16}/></button>) : <em>No matching documents</em>}</section></div>; }
function routeLabel(route) { return ({ assistant: 'Assistant', library: 'Library', insights: 'Insights', settings: 'Settings', help: 'Help center', upgrade: 'Upgrade' })[route] || 'Assistant'; }

function AuthScreen({ mode, navigate, notify, login, signup }) {
  const isSignup = mode === 'signup';
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      const user = isSignup
        ? await signup(name, email, password)
        : await login(email, password);
      notify(
        isSignup ? 'Your workspace is ready' : `Welcome back, ${user.name.split(' ')[0]}`,
        isSignup ? 'Start by adding your first PDF document.' : 'Your research library is synced and ready.',
      );
      navigate('assistant');
    } catch (error) {
      notify(isSignup ? 'Could not create your account' : 'Sign in failed', error.message);
    } finally {
      setLoading(false);
    }
  };
  return <main className="auth-shell">
    <section className="auth-story">
      <button className="auth-brand" onClick={() => navigate('login')}><span><Sparkles size={18}/></span>paperwise</button>
      <div className="auth-story-copy"><p className="auth-eyebrow">YOUR RESEARCH, CONNECTED</p><h1>Find the signal<br/>in every page.</h1><p>Paperwise turns your document library into a thoughtful research partner — clear, contextual, and always cited.</p></div>
      <div className="auth-quote"><div className="quote-spark"><Sparkles size={15}/></div><blockquote>“The fastest way our team has found to turn a stack of documents into one clear point of view.”</blockquote><div><strong>Priya Nair</strong><span>Head of Strategy, Noma</span></div></div>
      <div className="auth-orbit orbit-one"></div><div className="auth-orbit orbit-two"></div><div className="auth-dots"></div>
    </section>
    <section className="auth-panel">
      <div className="auth-form-wrap"><button className="mobile-auth-brand" onClick={() => navigate('login')}><span><Sparkles size={16}/></span>paperwise</button><div className="auth-heading"><p>{isSignup ? 'START YOUR WORKSPACE' : 'WELCOME BACK'}</p><h2>{isSignup ? 'Create an account' : 'Sign in to Paperwise'}</h2><span>{isSignup ? 'Already have an account?' : 'New to Paperwise?'} <button onClick={() => navigate(isSignup ? 'login' : 'signup')}>{isSignup ? 'Sign in' : 'Create an account'}</button></span></div>
        <div className="social-row"><button onClick={() => notify('Google sign-in', 'Google authentication is ready to connect to your identity provider.')}><span className="google-mark">G</span>Continue with Google</button><button className="github-button" onClick={() => notify('GitHub sign-in', 'GitHub authentication is ready to connect to your identity provider.')}><Github size={18}/></button></div>
        <div className="auth-divider"><span>OR CONTINUE WITH EMAIL</span></div>
        <form className="auth-form" onSubmit={submit}>{isSignup && <label>Full name<input required value={name} onChange={(e) => setName(e.target.value)} placeholder="Maya Singh" autoComplete="name"/></label>}<label>Email address<div className="field-icon"><Mail size={17}/><input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="maya@company.com" autoComplete="email"/></div></label><label>Password<div className="field-icon"><LockKeyhole size={17}/><input required type={showPassword ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} placeholder={isSignup ? 'Create a secure password' : 'Enter your password'} minLength="8" autoComplete={isSignup ? 'new-password' : 'current-password'}/><button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? <EyeOff size={17}/> : <Eye size={17}/>}</button></div></label>{isSignup ? <p className="terms"><CheckCircle2 size={15}/>By creating an account, you agree to our <button type="button" onClick={() => notify('Terms of service', 'Terms will open in a separate policy page when connected.')}>Terms</button> and <button type="button" onClick={() => notify('Privacy policy', 'Privacy policy will open in a separate policy page when connected.')}>Privacy Policy</button>.</p> : <button type="button" className="forgot-password" onClick={() => notify('Password reset', 'A secure reset link will be sent after the email service is connected.')}>Forgot password?</button>}<button className="auth-submit" disabled={loading}>{loading ? 'Just a moment…' : isSignup ? 'Create your workspace' : 'Sign in to workspace'}<ArrowRight size={18}/></button></form>
        <div className="auth-security"><ShieldCheck size={16}/>Your documents are private and encrypted.</div>
      </div>
    </section>
  </main>;
}

function Message({ message }) {
  const { user } = useAuth();
  const assistant = message.role === 'assistant';
  return <article className={`message ${assistant ? 'assistant-message' : 'user-message'}`}><div className="message-meta">{assistant ? <div className="assistant-badge"><Sparkles size={14}/></div> : <div className="avatar tiny">{getInitials(user?.name)}</div>}<strong>{assistant ? 'Paperwise' : 'You'}</strong><time>{message.time}</time></div><div className="message-content">{message.content.split('\n').map((line, i) => <p key={i}>{line || <br/>}</p>)}{message.sources && <div className="sources"><span><FileText size={14}/>Sources</span>{message.sources.map((source) => <button key={source} onClick={() => { window.location.hash = 'library'; }}>{source}</button>)}</div>}</div></article>;
}