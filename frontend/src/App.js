import React, { useState, useEffect, createContext, useContext } from 'react';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Theme Context
const ThemeContext = createContext();

const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    const savedTheme = localStorage.getItem('theme');
    return savedTheme || 'light';
  });

  useEffect(() => {
    localStorage.setItem('theme', theme);
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

// Auth Context
const AuthContext = createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchCurrentUser();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchCurrentUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      console.error('Error fetching user:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    const response = await axios.post(`${API}/auth/login`, { email, password });
    const { access_token, user: userData } = response.data;
    
    localStorage.setItem('token', access_token);
    setToken(access_token);
    setUser(userData);
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    
    return userData;
  };

  const register = async (name, email, password, role = 'user') => {
    const response = await axios.post(`${API}/auth/register`, { name, email, password, role });
    const { access_token, user: userData } = response.data;
    
    localStorage.setItem('token', access_token);
    setToken(access_token);
    setUser(userData);
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    
    return userData;
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Auth Components
const AuthForm = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    role: 'user' // Always user for new registrations
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLogin) {
        await login(formData.email, formData.password);
      } else {
        // Force role to user for registrations
        await register(formData.name, formData.email, formData.password, 'user');
      }
    } catch (error) {
      setError(error.response?.data?.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-800 relative overflow-hidden">
      {/* Background animated elements */}
      <div className="absolute inset-0">
        <div className="absolute top-10 left-10 w-72 h-72 bg-blue-400 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse"></div>
        <div className="absolute top-20 right-10 w-72 h-72 bg-purple-400 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse delay-2000"></div>
        <div className="absolute bottom-10 left-20 w-72 h-72 bg-pink-400 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse delay-4000"></div>
      </div>
      
      <div className="relative z-10 min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          {/* Logo and branding */}
          <div className="text-center">
            <div className="mx-auto h-20 w-20 bg-gradient-to-br from-blue-400 to-purple-600 rounded-2xl flex items-center justify-center mb-6 shadow-2xl">
              <svg className="h-10 w-10 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zm0 4a1 1 0 011-1h6a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h6a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <h2 className="text-4xl font-bold text-white mb-2">
              CRM Descomplica
            </h2>
            <p className="text-xl text-indigo-200 mb-6">
              {isLogin ? 'Bem-vindo de volta!' : 'Junte-se a nós!'}
            </p>
            <p className="text-sm text-indigo-300">
              Sistema Kanban inteligente para gestão de leads
            </p>
          </div>
          
          {/* Login Form */}
          <div className="backdrop-blur-lg bg-white/10 p-8 rounded-3xl shadow-2xl border border-white/20">
            <form onSubmit={handleSubmit} className="space-y-6">
              {error && (
                <div className="bg-red-500/20 border border-red-400/50 text-red-200 px-4 py-3 rounded-xl backdrop-blur-sm">
                  {error}
                </div>
              )}
              
              <div className="space-y-4">
                {!isLogin && (
                  <div className="relative">
                    <input
                      type="text"
                      required
                      placeholder="Nome completo"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="w-full px-6 py-4 bg-white/10 border border-white/20 rounded-2xl placeholder-white/60 text-white focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent backdrop-blur-sm transition-all duration-300"
                    />
                    <div className="absolute inset-y-0 right-0 pr-6 flex items-center">
                      <svg className="h-5 w-5 text-white/40" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                      </svg>
                    </div>
                  </div>
                )}
                
                <div className="relative">
                  <input
                    type="text"
                    required
                    placeholder={isLogin ? "Usuário ou Email" : "Email"}
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-6 py-4 bg-white/10 border border-white/20 rounded-2xl placeholder-white/60 text-white focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent backdrop-blur-sm transition-all duration-300"
                  />
                  <div className="absolute inset-y-0 right-0 pr-6 flex items-center">
                    <svg className="h-5 w-5 text-white/40" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                      <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
                    </svg>
                  </div>
                </div>
                
                <div className="relative">
                  <input
                    type="password"
                    required
                    placeholder="Senha"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="w-full px-6 py-4 bg-white/10 border border-white/20 rounded-2xl placeholder-white/60 text-white focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent backdrop-blur-sm transition-all duration-300"
                  />
                  <div className="absolute inset-y-0 right-0 pr-6 flex items-center">
                    <svg className="h-5 w-5 text-white/40" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                </div>
                
                {/* Role info for registration - showing it's automatically set to user */}
                {!isLogin && (
                  <div className="bg-blue-500/20 border border-blue-400/50 text-blue-200 px-4 py-3 rounded-xl backdrop-blur-sm text-sm">
                    ℹ️ Novos usuários são registrados automaticamente como <strong>Usuário</strong>
                  </div>
                )}
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-4 px-6 rounded-2xl hover:from-blue-700 hover:to-purple-700 focus:outline-none focus:ring-4 focus:ring-blue-500/50 transition-all duration-300 font-semibold text-lg shadow-2xl disabled:opacity-50 transform hover:scale-105"
              >
                {loading ? (
                  <div className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Processando...
                  </div>
                ) : (
                  isLogin ? '🚀 Entrar' : '✨ Registrar'
                )}
              </button>

              <div className="text-center">
                <button
                  type="button"
                  onClick={() => {
                    setIsLogin(!isLogin);
                    setError('');
                    setFormData({ name: '', email: '', password: '', role: 'user' });
                  }}
                  className="text-blue-300 hover:text-blue-200 font-medium text-lg transition-colors duration-200 underline decoration-2 underline-offset-4 hover:decoration-blue-300"
                >
                  {isLogin ? '✨ Não tem conta? Registre-se' : '🔐 Já tem conta? Entre'}
                </button>
              </div>
              
              {/* Demo users info */}
              {isLogin && (
                <div className="mt-6 p-4 bg-black/20 rounded-xl backdrop-blur-sm border border-white/10">
                  <p className="text-white/80 text-sm text-center mb-2">👥 <strong>Usuários Demo:</strong></p>
                  <div className="text-xs text-white/60 space-y-1">
                    <p><strong>Admin:</strong> admin / Rafa040388?</p>
                    <p><strong>Suporte:</strong> suporte / 25261020</p>
                  </div>
                </div>
              )}
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

// Stats Card Component
const StatsCard = ({ title, value, icon, color, subtitle }) => (
  <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-100 dark:border-gray-700 transition-colors duration-200">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">{title}</p>
        <p className={`text-2xl font-bold ${color}`}>{value}</p>
        {subtitle && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{subtitle}</p>}
      </div>
      <div className={`text-3xl ${color}`}>
        {icon}
      </div>
    </div>
  </div>
);

// Dashboard Component
const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardStats();
  }, []);

  const fetchDashboardStats = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-gray-200 dark:bg-gray-700 h-24 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value);
  };

  return (
    <div className="p-6 bg-gray-50 dark:bg-gray-900 min-h-screen transition-colors duration-200">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Dashboard</h2>
        <p className="text-gray-600 dark:text-gray-300">Visão geral dos seus leads e performance</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatsCard
          title="Total de Leads"
          value={stats?.total_leads || 0}
          icon="👥"
          color="text-blue-600"
          subtitle="leads ativos"
        />
        <StatsCard
          title="Taxa de Conversão"
          value={`${stats?.conversion_rate || 0}%`}
          icon="📈"
          color="text-green-600"
          subtitle="fechamentos ganhos"
        />
        <StatsCard
          title="Ticket Médio"
          value={formatCurrency(stats?.avg_deal_size || 0)}
          icon="💰"
          color="text-yellow-600"
          subtitle="por lead fechado"
        />
        <StatsCard
          title="Pipeline Valor"
          value={formatCurrency(
            Object.values(stats?.status_stats || {}).reduce(
              (sum, stat) => sum + (stat.value || 0), 0
            )
          )}
          icon="🎯"
          color="text-purple-600"
          subtitle="valor total em pipeline"
        />
      </div>

      {/* Status Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-100 dark:border-gray-700 transition-colors duration-200">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Distribuição por Status</h3>
          <div className="space-y-3">
            {stats?.status_stats && Object.entries(stats.status_stats).map(([status, data]) => {
              const statusLabels = {
                'novo': 'Novo',
                'qualificado': 'Qualificado',
                'proposta': 'Proposta',
                'negociacao': 'Negociação',
                'fechado_ganho': 'Fechado (Ganho)',
                'fechado_perdido': 'Fechado (Perdido)'
              };
              
              const colors = {
                'novo': 'bg-blue-500',
                'qualificado': 'bg-green-500',
                'proposta': 'bg-yellow-500',
                'negociacao': 'bg-red-500',
                'fechado_ganho': 'bg-green-600',
                'fechado_perdido': 'bg-gray-500'
              };

              return (
                <div key={status} className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className={`w-3 h-3 rounded-full ${colors[status]} mr-3`}></div>
                    <span className="text-sm text-gray-700 dark:text-gray-300">{statusLabels[status]}</span>
                  </div>
                  <div className="flex items-center space-x-4">
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {data.count} leads
                    </span>
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {formatCurrency(data.value || 0)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-100 dark:border-gray-700 transition-colors duration-200">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Atividades Recentes</h3>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {stats?.recent_activities?.slice(0, 8).map((activity, index) => (
              <div key={index} className="flex items-start space-x-3 p-2 hover:bg-gray-50 dark:hover:bg-gray-700 rounded transition-colors duration-200">
                <div className="flex-shrink-0 w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-900 dark:text-white truncate">
                    {activity.details}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {new Date(activity.timestamp).toLocaleString('pt-BR')}
                  </p>
                </div>
              </div>
            )) || (
              <p className="text-gray-500 dark:text-gray-400 text-sm">Nenhuma atividade recente</p>
            )}
          </div>
        </div>
      </div>

      {/* Top Sources */}
      {stats?.top_sources?.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-100 dark:border-gray-700 transition-colors duration-200">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Top Fontes de Leads</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {stats.top_sources.map((source, index) => (
              <div key={index} className="text-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 transition-colors duration-200">
                <p className="font-medium text-gray-900 dark:text-white">{source._id || 'Não informado'}</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">{source.count} leads</p>
                <p className="text-sm text-green-600 dark:text-green-400">{formatCurrency(source.total_value || 0)}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// Removed Calendar component as per user request - no Google Calendar integration needed

// Kanban Components (existing code remains the same)
const LeadCard = ({ lead, onDragStart }) => {
  const formatCurrency = (value) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value);
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('pt-BR');
  };

  const priorityColors = {
    high: 'border-red-500 bg-red-50 dark:bg-red-900/20',
    medium: 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20',
    low: 'border-green-500 bg-green-50 dark:bg-green-900/20'
  };

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, lead)}
      className={`bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 mb-3 cursor-move hover:shadow-lg transition-all duration-200 border-l-4 ${priorityColors[lead.priority] || 'border-blue-500'}`}
    >
      <div className="flex justify-between items-start mb-2">
        <h4 className="font-semibold text-gray-900 dark:text-white text-sm">{lead.title}</h4>
        {lead.priority === 'high' && <span className="text-red-500 text-xs">🔴</span>}
      </div>
      
      {lead.company && (
        <p className="text-sm text-gray-600 dark:text-gray-300 mb-1">🏢 {lead.company}</p>
      )}
      {lead.contact_name && (
        <p className="text-sm text-gray-600 dark:text-gray-300 mb-1">👤 {lead.contact_name}</p>
      )}
      {lead.email && (
        <p className="text-sm text-blue-600 dark:text-blue-400 mb-1">📧 {lead.email}</p>
      )}
      {lead.value > 0 && (
        <p className="text-sm font-semibold text-green-600 dark:text-green-400 mb-1">
          💰 {formatCurrency(lead.value)}
        </p>
      )}
      
      {lead.next_follow_up && (
        <p className="text-xs text-orange-600 dark:text-orange-400 mb-2">
          🔔 Follow-up: {formatDate(lead.next_follow_up)}
        </p>
      )}
      
      {lead.tags && lead.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {lead.tags.slice(0, 3).map((tag, index) => (
            <span
              key={index}
              className="bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 text-xs px-2 py-1 rounded-full"
            >
              {tag}
            </span>
          ))}
          {lead.tags.length > 3 && (
            <span className="text-xs text-gray-500 dark:text-gray-400">+{lead.tags.length - 3}</span>
          )}
        </div>
      )}
      
      <div className="flex justify-between items-center text-xs text-gray-500 dark:text-gray-400 mt-2">
        <span>{formatDate(lead.created_at)}</span>
        <div className="flex items-center space-x-1">
          {lead.source && (
            <span className="bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 px-2 py-1 rounded text-xs">{lead.source}</span>
          )}
          {lead.assigned_to && (
            <span className="bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">👤</span>
          )}
        </div>
      </div>
    </div>
  );
};

const KanbanColumn = ({ column, onDrop, onDragOver }) => {
  const totalValue = column.leads.reduce((sum, lead) => sum + (lead.value || 0), 0);
  
  const formatCurrency = (value) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value);
  };

  return (
    <div
      className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 min-h-96 min-w-80 border border-gray-200 dark:border-gray-700 transition-colors duration-200"
      onDrop={(e) => onDrop(e, column.status)}
      onDragOver={onDragOver}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <h3 className="font-bold text-lg text-gray-800 dark:text-white">{column.title}</h3>
          <span
            className="w-4 h-4 rounded-full"
            style={{ backgroundColor: column.color }}
          ></span>
        </div>
        <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
          {column.leads.length}
        </span>
      </div>
      
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {column.leads.map((lead) => (
          <LeadCard
            key={lead.id}
            lead={lead}
            onDragStart={(e, lead) => {
              e.dataTransfer.setData('text/plain', JSON.stringify(lead));
            }}
          />
        ))}
      </div>
      
      <div className="text-sm text-gray-500 mt-4 pt-2 border-t border-gray-200">
        <div className="flex justify-between">
          <span>{column.leads.length} lead{column.leads.length !== 1 ? 's' : ''}</span>
          {totalValue > 0 && (
            <span className="text-green-600 font-medium">
              {formatCurrency(totalValue)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

const NewLeadForm = ({ onClose, onSubmit }) => {
  const [formData, setFormData] = useState({
    title: '',
    company: '',
    contact_name: '',
    email: '',
    phone: '',
    status: 'novo',
    tags: '',
    notes: '',
    value: '',
    priority: 'medium',
    assigned_to: '',
    source: '',
    next_follow_up: '',
    expected_close_date: ''
  });
  
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const leadData = {
        ...formData,
        tags: formData.tags ? formData.tags.split(',').map(tag => tag.trim()) : [],
        value: parseFloat(formData.value) || 0,
        next_follow_up: formData.next_follow_up ? new Date(formData.next_follow_up).toISOString() : null,
        expected_close_date: formData.expected_close_date ? new Date(formData.expected_close_date).toISOString() : null
      };
      await onSubmit(leadData);
      onClose();
    } catch (error) {
      console.error('Error creating lead:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-4xl max-h-96 overflow-y-auto m-4 border border-gray-200 dark:border-gray-700">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">Novo Lead</h3>
          <button
            onClick={onClose}
            className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 text-xl transition-colors duration-200"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Título *
              </label>
              <input
                type="text"
                required
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-white transition-colors duration-200"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Empresa
              </label>
              <input
                type="text"
                value={formData.company}
                onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-white transition-colors duration-200"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Nome do Contato
              </label>
              <input
                type="text"
                value={formData.contact_name}
                onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-white transition-colors duration-200"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Email
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-white transition-colors duration-200"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Telefone
              </label>
              <input
                type="text"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-white transition-colors duration-200"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Valor (R$)
              </label>
              <input
                type="number"
                step="0.01"
                value={formData.value}
                onChange={(e) => setFormData({ ...formData, value: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-white transition-colors duration-200"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Prioridade
              </label>
              <select
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-white transition-colors duration-200"
              >
                <option value="low">Baixa</option>
                <option value="medium">Média</option>
                <option value="high">Alta</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Fonte
              </label>
              <input
                type="text"
                value={formData.source}
                onChange={(e) => setFormData({ ...formData, source: e.target.value })}
                placeholder="website, referral, cold_call..."
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-white transition-colors duration-200"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Próximo Follow-up
              </label>
              <input
                type="datetime-local"
                value={formData.next_follow_up}
                onChange={(e) => setFormData({ ...formData, next_follow_up: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-white transition-colors duration-200"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Tags (separadas por vírgula)
              </label>
              <input
                type="text"
                value={formData.tags}
                onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                placeholder="marketing, urgente, vip"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Data Esperada de Fechamento
              </label>
              <input
                type="date"
                value={formData.expected_close_date}
                onChange={(e) => setFormData({ ...formData, expected_close_date: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="md:col-span-3">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Observações
              </label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                rows="3"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Salvando...' : 'Criar Lead'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const KanbanBoard = () => {
  const [kanbanData, setKanbanData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNewLeadForm, setShowNewLeadForm] = useState(false);
  const { user } = useAuth();

  useEffect(() => {
    fetchKanbanData();
  }, []);

  const fetchKanbanData = async () => {
    try {
      const response = await axios.get(`${API}/kanban`);
      setKanbanData(response.data);
    } catch (error) {
      console.error('Error fetching kanban data:', error);
    } finally {
      setLoading(false);
    }
  };

  const createLead = async (leadData) => {
    try {
      await axios.post(`${API}/leads`, leadData);
      fetchKanbanData(); // Refresh the board
    } catch (error) {
      console.error('Error creating lead:', error);
      throw error;
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = async (e, newStatus) => {
    e.preventDefault();
    const leadData = JSON.parse(e.dataTransfer.getData('text/plain'));
    
    if (leadData.status === newStatus) {
      return; // No change needed
    }

    try {
      await axios.post(`${API}/kanban/move`, {
        lead_id: leadData.id,
        new_status: newStatus,
        new_position: 0
      });
      fetchKanbanData(); // Refresh the board
    } catch (error) {
      console.error('Error moving lead:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
        <div className="text-xl text-gray-900 dark:text-white">Carregando...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 transition-colors duration-200">
      {/* Kanban Board */}
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Pipeline de Vendas</h1>
            <p className="text-gray-600 dark:text-gray-300">Gerencie seus leads através do funil de vendas</p>
          </div>
          <button
            onClick={() => setShowNewLeadForm(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg flex items-center gap-2 transition-colors duration-200"
          >
            ➕ Novo Lead
          </button>
        </div>

        <div className="flex gap-6 overflow-x-auto pb-4">
          {kanbanData.map((column) => (
            <KanbanColumn
              key={column.status}
              column={column}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
            />
          ))}
        </div>
      </div>

      {/* New Lead Form Modal */}
      {showNewLeadForm && (
        <NewLeadForm
          onClose={() => setShowNewLeadForm(false)}
          onSubmit={createLead}
        />
      )}
    </div>
  );
};

// Automations Component
const Automations = () => {
  const [rules, setRules] = useState([]);
  const [showRuleForm, setShowRuleForm] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAutomationRules();
  }, []);

  const fetchAutomationRules = async () => {
    try {
      const response = await axios.get(`${API}/automation/rules`);
      setRules(response.data);
    } catch (error) {
      console.error('Error fetching automation rules:', error);
    } finally {
      setLoading(false);
    }
  };

  const createAutomationRule = async (ruleData) => {
    try {
      await axios.post(`${API}/automation/rules`, ruleData);
      fetchAutomationRules();
      setShowRuleForm(false);
    } catch (error) {
      console.error('Error creating automation rule:', error);
      throw error;
    }
  };

  const statusOptions = [
    { value: 'novo', label: 'Novo' },
    { value: 'qualificado', label: 'Qualificado' },
    { value: 'proposta', label: 'Proposta' },
    { value: 'negociacao', label: 'Negociação' },
    { value: 'fechado_ganho', label: 'Fechado (Ganho)' },
    { value: 'fechado_perdido', label: 'Fechado (Perdido)' }
  ];

  const actionOptions = [
    { value: 'schedule_follow_up', label: 'Agendar Follow-up', params: [{ key: 'days', label: 'Dias', type: 'number' }] },
    { value: 'create_task', label: 'Criar Tarefa', params: [{ key: 'task_description', label: 'Descrição', type: 'text' }] },
    { value: 'send_email', label: 'Enviar Email', params: [{ key: 'email_template', label: 'Template', type: 'text' }] }
  ];

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Automações</h2>
          <p className="text-gray-600">Configure regras automáticas para seus leads</p>
        </div>
        <button
          onClick={() => setShowRuleForm(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          ➕ Nova Regra
        </button>
      </div>

      <div className="grid gap-6">
        {loading ? (
          <div className="bg-white rounded-lg p-6 shadow-lg">
            <div className="animate-pulse space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 bg-gray-200 rounded"></div>
              ))}
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-lg">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Regras Ativas</h3>
              {rules.length > 0 ? (
                <div className="space-y-4">
                  {rules.map((rule) => (
                    <div key={rule.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <h4 className="font-medium text-gray-900">{rule.name}</h4>
                          <div className="text-sm text-gray-600 mt-1">
                            <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs mr-2">
                              Quando: {statusOptions.find(s => s.value === rule.trigger_status)?.label}
                            </span>
                            <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs">
                              Ação: {actionOptions.find(a => a.value === rule.action)?.label}
                            </span>
                          </div>
                          {Object.keys(rule.action_params).length > 0 && (
                            <div className="text-xs text-gray-500 mt-2">
                              Parâmetros: {JSON.stringify(rule.action_params)}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className={`px-2 py-1 rounded-full text-xs ${
                            rule.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                          }`}>
                            {rule.is_active ? 'Ativa' : 'Inativa'}
                          </span>
                          <span className="text-xs text-gray-500">
                            {new Date(rule.created_at).toLocaleDateString('pt-BR')}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-gray-500">Nenhuma regra de automação criada</p>
                  <button
                    onClick={() => setShowRuleForm(true)}
                    className="mt-2 text-blue-600 hover:text-blue-700"
                  >
                    Criar primeira regra
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* New Rule Form Modal */}
      {showRuleForm && (
        <AutomationRuleForm
          onClose={() => setShowRuleForm(false)}
          onSubmit={createAutomationRule}
          statusOptions={statusOptions}
          actionOptions={actionOptions}
        />
      )}
    </div>
  );
};

// Automation Rule Form Component
const AutomationRuleForm = ({ onClose, onSubmit, statusOptions, actionOptions }) => {
  const [formData, setFormData] = useState({
    name: '',
    trigger_status: '',
    action: '',
    action_params: {}
  });
  const [loading, setLoading] = useState(false);

  const selectedAction = actionOptions.find(a => a.value === formData.action);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await onSubmit(formData);
    } catch (error) {
      console.error('Error creating rule:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleActionParamChange = (paramKey, value) => {
    setFormData({
      ...formData,
      action_params: {
        ...formData.action_params,
        [paramKey]: value
      }
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-96 overflow-y-auto m-4">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-xl font-bold text-gray-900">Nova Regra de Automação</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700 text-xl">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nome da Regra *</label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Ex: Auto follow-up para leads qualificados"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Gatilho (Quando) *</label>
            <select
              required
              value={formData.trigger_status}
              onChange={(e) => setFormData({ ...formData, trigger_status: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Selecione o status que dispara a regra</option>
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Ação *</label>
            <select
              required
              value={formData.action}
              onChange={(e) => setFormData({ ...formData, action: e.target.value, action_params: {} })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Selecione a ação a ser executada</option>
              {actionOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>

          {/* Dynamic action parameters */}
          {selectedAction && selectedAction.params && (
            <div className="space-y-3">
              <h4 className="font-medium text-gray-900">Parâmetros da Ação</h4>
              {selectedAction.params.map((param) => (
                <div key={param.key}>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{param.label}</label>
                  <input
                    type={param.type}
                    value={formData.action_params[param.key] || ''}
                    onChange={(e) => handleActionParamChange(param.key, e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              ))}
            </div>
          )}

          <div className="flex justify-end space-x-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Criando...' : 'Criar Regra'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Theme Manager Component
const ThemeManager = () => {
  const [activeTheme, setActiveTheme] = useState(null);
  const [themes, setThemes] = useState([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [newTheme, setNewTheme] = useState({
    name: '',
    colors: {
      primary: '#3b82f6',
      secondary: '#6b7280',
      success: '#10b981',
      warning: '#f59e0b',
      danger: '#ef4444',
      background: '#f8fafc',
      surface: '#ffffff',
      text_primary: '#1e293b',
      text_secondary: '#64748b'
    },
    font_family: 'Inter, system-ui, sans-serif',
    font_size_base: '14px',
    border_radius: '0.5rem',
    is_dark_mode: false
  });
  const [logoFile, setLogoFile] = useState(null);

  useEffect(() => {
    fetchThemes();
    fetchActiveTheme();
  }, []);

  const fetchThemes = async () => {
    try {
      const response = await axios.get(`${API}/themes`);
      setThemes(response.data);
    } catch (error) {
      console.error('Error fetching themes:', error);
    }
  };

  const fetchActiveTheme = async () => {
    try {
      const response = await axios.get(`${API}/themes/active`);
      setActiveTheme(response.data);
      applyTheme(response.data);
    } catch (error) {
      console.error('Error fetching active theme:', error);
    }
  };

  const applyTheme = (theme) => {
    const root = document.documentElement;
    Object.entries(theme.colors).forEach(([key, value]) => {
      root.style.setProperty(`--color-${key.replace('_', '-')}`, value);
    });
    root.style.setProperty('--font-family', theme.font_family);
    root.style.setProperty('--font-size-base', theme.font_size_base);
    root.style.setProperty('--border-radius', theme.border_radius);
    
    if (theme.is_dark_mode) {
      document.body.classList.add('dark');
    } else {
      document.body.classList.remove('dark');
    }
  };

  const handleLogoUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const base64String = e.target.result;
        setNewTheme(prev => ({ ...prev, logo_base64: base64String }));
        setLogoFile(file);
      };
      reader.readAsDataURL(file);
    }
  };

  const createTheme = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${API}/themes`, newTheme);
      await fetchThemes();
      setShowCreateForm(false);
      setNewTheme({
        name: '',
        colors: {
          primary: '#3b82f6',
          secondary: '#6b7280',
          success: '#10b981',
          warning: '#f59e0b',
          danger: '#ef4444',
          background: '#f8fafc',
          surface: '#ffffff',
          text_primary: '#1e293b',
          text_secondary: '#64748b'
        },
        font_family: 'Inter, system-ui, sans-serif',
        font_size_base: '14px',
        border_radius: '0.5rem',
        is_dark_mode: false
      });
      setLogoFile(null);
    } catch (error) {
      console.error('Error creating theme:', error);
    }
    setLoading(false);
  };

  const activateTheme = async (themeId) => {
    try {
      await axios.post(`${API}/themes/${themeId}/activate`);
      await fetchActiveTheme();
      await fetchThemes();
    } catch (error) {
      console.error('Error activating theme:', error);
    }
  };

  const deleteTheme = async (themeId) => {
    if (window.confirm('Tem certeza que deseja excluir este tema?')) {
      try {
        await axios.delete(`${API}/themes/${themeId}`);
        await fetchThemes();
      } catch (error) {
        console.error('Error deleting theme:', error);
      }
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Gerenciamento de Temas</h1>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          {showCreateForm ? 'Cancelar' : '+ Novo Tema'}
        </button>
      </div>

      {/* Create Theme Form */}
      {showCreateForm && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-semibold mb-4">Criar Novo Tema</h2>
          <form onSubmit={createTheme} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Nome do Tema</label>
              <input
                type="text"
                value={newTheme.name}
                onChange={(e) => setNewTheme(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                required
              />
            </div>

            {/* Color Palette */}
            <div>
              <h3 className="text-lg font-medium mb-4">Paleta de Cores</h3>
              <div className="grid grid-cols-3 gap-4">
                {Object.entries(newTheme.colors).map(([key, value]) => (
                  <div key={key}>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 capitalize">
                      {key.replace('_', ' ')}
                    </label>
                    <div className="flex items-center space-x-2">
                      <input
                        type="color"
                        value={value}
                        onChange={(e) => setNewTheme(prev => ({
                          ...prev,
                          colors: { ...prev.colors, [key]: e.target.value }
                        }))}
                        className="w-12 h-10 rounded border border-gray-300"
                      />
                      <span className="text-sm text-gray-600">{value}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Logo Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Logo (Opcional)</label>
              <input
                type="file"
                accept="image/*"
                onChange={handleLogoUpload}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              {logoFile && (
                <div className="mt-2">
                  <img 
                    src={newTheme.logo_base64} 
                    alt="Logo preview" 
                    className="h-16 w-auto rounded border"
                  />
                </div>
              )}
            </div>

            {/* Typography */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Fonte</label>
                <select
                  value={newTheme.font_family}
                  onChange={(e) => setNewTheme(prev => ({ ...prev, font_family: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="Inter, system-ui, sans-serif">Inter</option>
                  <option value="Roboto, sans-serif">Roboto</option>
                  <option value="Open Sans, sans-serif">Open Sans</option>
                  <option value="Lato, sans-serif">Lato</option>
                  <option value="Montserrat, sans-serif">Montserrat</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Tamanho Base</label>
                <select
                  value={newTheme.font_size_base}
                  onChange={(e) => setNewTheme(prev => ({ ...prev, font_size_base: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="12px">12px (Pequeno)</option>
                  <option value="14px">14px (Normal)</option>
                  <option value="16px">16px (Grande)</option>
                  <option value="18px">18px (Extra Grande)</option>
                </select>
              </div>
            </div>

            {/* Border Radius */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Bordas Arredondadas</label>
              <select
                value={newTheme.border_radius}
                onChange={(e) => setNewTheme(prev => ({ ...prev, border_radius: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="0">Sem arredondamento</option>
                <option value="0.25rem">Pequeno</option>
                <option value="0.5rem">Médio</option>
                <option value="0.75rem">Grande</option>
                <option value="1rem">Extra Grande</option>
              </select>
            </div>

            {/* Dark Mode */}
            <div className="flex items-center">
              <input
                type="checkbox"
                id="dark_mode"
                checked={newTheme.is_dark_mode}
                onChange={(e) => setNewTheme(prev => ({ ...prev, is_dark_mode: e.target.checked }))}
                className="mr-2"
              />
              <label htmlFor="dark_mode" className="text-sm font-medium text-gray-700">
                Modo Escuro
              </label>
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={loading}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {loading ? 'Criando...' : 'Criar Tema'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Themes List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {themes.map((theme) => (
          <div key={theme.id} className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-start mb-4">
              <h3 className="font-semibold text-lg">{theme.name}</h3>
              {theme.is_active && (
                <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full">
                  Ativo
                </span>
              )}
            </div>

            {/* Color Preview */}
            <div className="flex space-x-1 mb-4">
              {Object.values(theme.colors).slice(0, 5).map((color, index) => (
                <div
                  key={index}
                  className="w-6 h-6 rounded"
                  style={{ backgroundColor: color }}
                ></div>
              ))}
            </div>

            {/* Logo Preview */}
            {theme.logo_base64 && (
              <div className="mb-4">
                <img 
                  src={theme.logo_base64} 
                  alt={`${theme.name} logo`} 
                  className="h-12 w-auto rounded border"
                />
              </div>
            )}

            <div className="text-sm text-gray-600 mb-4">
              <p>Fonte: {theme.font_family.split(',')[0]}</p>
              <p>Modo: {theme.is_dark_mode ? 'Escuro' : 'Claro'}</p>
            </div>

            <div className="flex space-x-2">
              {!theme.is_active && (
                <button
                  onClick={() => activateTheme(theme.id)}
                  className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 transition-colors"
                >
                  Ativar
                </button>
              )}
              {!theme.is_active && (
                <button
                  onClick={() => deleteTheme(theme.id)}
                  className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700 transition-colors"
                >
                  Excluir
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Webhook Manager Component
const WebhookManager = () => {
  const [webhooks, setWebhooks] = useState([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [newWebhook, setNewWebhook] = useState({
    name: '',
    url: '',
    events: [],
    retry_count: 3,
    timeout_seconds: 30
  });
  const [webhookLogs, setWebhookLogs] = useState({});
  const [showLogs, setShowLogs] = useState({});

  const eventOptions = [
    { value: 'lead.created', label: 'Lead Criado' },
    { value: 'lead.updated', label: 'Lead Atualizado' },
    { value: 'lead.status_changed', label: 'Status do Lead Alterado' },
    { value: 'lead.deleted', label: 'Lead Deletado' },
    { value: 'user.registered', label: 'Usuário Registrado' }
  ];

  useEffect(() => {
    fetchWebhooks();
  }, []);

  const fetchWebhooks = async () => {
    try {
      const response = await axios.get(`${API}/webhooks`);
      setWebhooks(response.data);
    } catch (error) {
      console.error('Error fetching webhooks:', error);
    }
  };

  const createWebhook = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${API}/webhooks`, newWebhook);
      await fetchWebhooks();
      setShowCreateForm(false);
      setNewWebhook({
        name: '',
        url: '',
        events: [],
        retry_count: 3,
        timeout_seconds: 30
      });
    } catch (error) {
      console.error('Error creating webhook:', error);
    }
    setLoading(false);
  };

  const deleteWebhook = async (webhookId) => {
    if (window.confirm('Tem certeza que deseja excluir este webhook?')) {
      try {
        await axios.delete(`${API}/webhooks/${webhookId}`);
        await fetchWebhooks();
      } catch (error) {
        console.error('Error deleting webhook:', error);
      }
    }
  };

  const testWebhook = async (webhookId) => {
    try {
      await axios.post(`${API}/webhooks/${webhookId}/test`);
      alert('Webhook de teste enviado!');
    } catch (error) {
      console.error('Error testing webhook:', error);
      alert('Erro ao enviar webhook de teste');
    }
  };

  const fetchWebhookLogs = async (webhookId) => {
    try {
      const response = await axios.get(`${API}/webhooks/${webhookId}/logs`);
      setWebhookLogs(prev => ({ ...prev, [webhookId]: response.data }));
      setShowLogs(prev => ({ ...prev, [webhookId]: true }));
    } catch (error) {
      console.error('Error fetching webhook logs:', error);
    }
  };

  const toggleEventSelect = (event) => {
    setNewWebhook(prev => ({
      ...prev,
      events: prev.events.includes(event)
        ? prev.events.filter(e => e !== event)
        : [...prev.events, event]
    }));
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Gerenciamento de Webhooks</h1>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          {showCreateForm ? 'Cancelar' : '+ Novo Webhook'}
        </button>
      </div>

      {/* Create Webhook Form */}
      {showCreateForm && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-semibold mb-4">Criar Novo Webhook</h2>
          <form onSubmit={createWebhook} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Nome</label>
              <input
                type="text"
                value={newWebhook.name}
                onChange={(e) => setNewWebhook(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">URL</label>
              <input
                type="url"
                value={newWebhook.url}
                onChange={(e) => setNewWebhook(prev => ({ ...prev, url: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="https://exemplo.com/webhook"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Eventos</label>
              <div className="space-y-2">
                {eventOptions.map((option) => (
                  <label key={option.value} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={newWebhook.events.includes(option.value)}
                      onChange={() => toggleEventSelect(option.value)}
                      className="mr-2"
                    />
                    <span className="text-sm">{option.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Tentativas</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={newWebhook.retry_count}
                  onChange={(e) => setNewWebhook(prev => ({ ...prev, retry_count: parseInt(e.target.value) }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Timeout (segundos)</label>
                <input
                  type="number"
                  min="5"
                  max="120"
                  value={newWebhook.timeout_seconds}
                  onChange={(e) => setNewWebhook(prev => ({ ...prev, timeout_seconds: parseInt(e.target.value) }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={loading || newWebhook.events.length === 0}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {loading ? 'Criando...' : 'Criar Webhook'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Webhooks List */}
      <div className="space-y-6">
        {webhooks.map((webhook) => (
          <div key={webhook.id} className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="font-semibold text-lg">{webhook.name}</h3>
                <p className="text-sm text-gray-600">{webhook.url}</p>
              </div>
              <div className="flex items-center space-x-2">
                {webhook.is_active ? (
                  <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full">
                    Ativo
                  </span>
                ) : (
                  <span className="bg-red-100 text-red-800 text-xs px-2 py-1 rounded-full">
                    Inativo
                  </span>
                )}
              </div>
            </div>

            {/* Events */}
            <div className="mb-4">
              <p className="text-sm font-medium text-gray-700 mb-2">Eventos:</p>
              <div className="flex flex-wrap gap-2">
                {webhook.events.map((event) => (
                  <span key={event} className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
                    {eventOptions.find(e => e.value === event)?.label || event}
                  </span>
                ))}
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4 mb-4 text-sm">
              <div>
                <p className="text-gray-600">Total de Disparos</p>
                <p className="font-semibold">{webhook.total_triggers}</p>
              </div>
              <div>
                <p className="text-gray-600">Falhas</p>
                <p className="font-semibold text-red-600">{webhook.failed_triggers}</p>
              </div>
              <div>
                <p className="text-gray-600">Última Execução</p>
                <p className="font-semibold">
                  {webhook.last_triggered 
                    ? new Date(webhook.last_triggered).toLocaleString('pt-BR')
                    : 'Nunca'
                  }
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex space-x-2">
              <button
                onClick={() => testWebhook(webhook.id)}
                className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700 transition-colors"
              >
                Testar
              </button>
              <button
                onClick={() => fetchWebhookLogs(webhook.id)}
                className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 transition-colors"
              >
                Ver Logs
              </button>
              <button
                onClick={() => deleteWebhook(webhook.id)}
                className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700 transition-colors"
              >
                Excluir
              </button>
            </div>

            {/* Webhook Logs */}
            {showLogs[webhook.id] && webhookLogs[webhook.id] && (
              <div className="mt-4 border-t pt-4">
                <div className="flex justify-between items-center mb-2">
                  <h4 className="font-medium">Logs de Execução</h4>
                  <button
                    onClick={() => setShowLogs(prev => ({ ...prev, [webhook.id]: false }))}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    ✕
                  </button>
                </div>
                <div className="max-h-64 overflow-y-auto space-y-2">
                  {webhookLogs[webhook.id].map((log) => (
                    <div key={log.id} className={`p-2 rounded text-sm ${
                      log.success ? 'bg-green-50 border-l-4 border-green-400' : 'bg-red-50 border-l-4 border-red-400'
                    }`}>
                      <div className="flex justify-between items-center">
                        <span className="font-medium">{log.event}</span>
                        <span className="text-xs text-gray-500">
                          {new Date(log.triggered_at).toLocaleString('pt-BR')}
                        </span>
                      </div>
                      {log.response_status && (
                        <div className="text-xs mt-1">
                          Status: {log.response_status}
                          {log.error_message && (
                            <div className="text-red-600 mt-1">{log.error_message}</div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {webhooks.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">Nenhum webhook configurado.</p>
        </div>
      )}
    </div>
  );
};

// Main Dashboard Component with Navigation
const MainDashboard = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const { logout, user } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'kanban', label: 'Kanban', icon: '📋' },
    { id: 'reports', label: 'Relatórios', icon: '📈' },
    { id: 'automations', label: 'Automações', icon: '🤖' },
    { id: 'themes', label: 'Temas', icon: '🎨' },
    { id: 'webhooks', label: 'Webhooks', icon: '🔗' },
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />;
      case 'kanban':
        return <KanbanBoard />;
      case 'automations':
        return <Automations />;
      case 'themes':
        return <ThemeManager />;
      case 'webhooks':
        return <WebhookManager />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 transition-colors duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-8">
              <div>
                <h1 className="text-xl font-bold text-gray-900 dark:text-white">CRM Kanban</h1>
                <p className="text-sm text-gray-600 dark:text-gray-300">Bem-vindo, {user?.name}!</p>
              </div>
              <nav className="flex space-x-1">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      activeTab === tab.id
                        ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 border-b-2 border-blue-600'
                        : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    <span>{tab.icon}</span>
                    <span>{tab.label}</span>
                  </button>
                ))}
              </nav>
            </div>
            <div className="flex items-center space-x-4">
              {/* Theme Toggle Button */}
              <button
                onClick={toggleTheme}
                className="p-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors duration-200"
                title={theme === 'light' ? 'Ativar modo escuro' : 'Ativar modo claro'}
              >
                {theme === 'light' ? (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                  </svg>
                )}
              </button>
              
              <div className="text-sm text-gray-600 dark:text-gray-300">
                <span className="font-medium capitalize">{user?.role}</span>
              </div>
              <button
                onClick={logout}
                className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-200"
              >
                Sair
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main>{renderContent()}</main>
    </div>
  );
};

// Main App Component
function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="loading-spinner mx-auto mb-4"></div>
          <p className="text-gray-600">Carregando...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      {user ? <MainDashboard /> : <AuthForm />}
    </div>
  );
}

// Root App with AuthProvider
export default function RootApp() {
  return (
    <AuthProvider>
      <App />
    </AuthProvider>
  );
}