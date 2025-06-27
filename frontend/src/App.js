import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, Link, useNavigate, useLocation, useParams } from 'react-router-dom';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID;

// Context for cart and user
const DeviceContext = createContext();

const useDeviceContext = () => {
  const context = useContext(DeviceContext);
  if (!context) {
    throw new Error('useDeviceContext must be used within DeviceProvider');
  }
  return context;
};

const DeviceProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [cart, setCart] = useState({ items: [] });
  const [sessionId] = useState(() => {
    let id = localStorage.getItem('sessionId');
    if (!id) {
      id = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('sessionId', id);
    }
    return id;
  });

  // Check for stored auth token
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUserInfo();
    }
  }, []);

  // Keep-alive system to prevent backend from sleeping
  useEffect(() => {
    const keepAlive = async () => {
      try {
        await axios.get(`${API}/health`);
        console.log('Backend keep-alive ping sent');
      } catch (error) {
        console.warn('Keep-alive ping failed:', error);
      }
    };

    keepAlive();
    const intervalId = setInterval(keepAlive, 10 * 60 * 1000);
    return () => clearInterval(intervalId);
  }, []);

  const fetchUserInfo = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      localStorage.removeItem('token');
      delete axios.defaults.headers.common['Authorization'];
      setUser(null);
    }
  };

  const login = (token, userData) => {
    localStorage.setItem('token', token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
  };

  const loadCart = async () => {
    try {
      const response = await axios.get(`${API}/cart/${sessionId}`);
      setCart(response.data);
    } catch (error) {
      console.error('Error loading cart:', error);
    }
  };

  const addToCart = async (productId, quantity = 1, subscriptionType = null) => {
    try {
      const response = await axios.post(`${API}/cart/${sessionId}/add`, {
        product_id: productId,
        quantity,
        subscription_type: subscriptionType
      });
      setCart(response.data);
      return true;
    } catch (error) {
      console.error('Error adding to cart:', error);
      return false;
    }
  };

  const removeFromCart = async (productId, subscriptionType = null) => {
    try {
      const response = await axios.delete(
        `${API}/cart/${sessionId}/remove/${productId}${subscriptionType ? `?subscription_type=${subscriptionType}` : ''}`
      );
      setCart(response.data);
    } catch (error) {
      console.error('Error removing from cart:', error);
    }
  };

  const applyCoupon = async (couponCode) => {
    try {
      const response = await axios.post(`${API}/cart/${sessionId}/apply-coupon?coupon_code=${couponCode}`);
      setCart(response.data);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || 'Cupão inválido' };
    }
  };

  const removeCoupon = async () => {
    try {
      const response = await axios.delete(`${API}/cart/${sessionId}/remove-coupon`);
      setCart(response.data);
    } catch (error) {
      console.error('Error removing coupon:', error);
    }
  };

  useEffect(() => {
    loadCart();
  }, []);

  return (
    <DeviceContext.Provider value={{
      user,
      setUser,
      cart,
      setCart,
      sessionId,
      loadCart,
      addToCart,
      removeFromCart,
      applyCoupon,
      removeCoupon,
      login,
      logout
    }}>
      {children}
    </DeviceContext.Provider>
  );
};

// Google OAuth Component
const GoogleLoginButton = ({ onSuccess, onError }) => {
  useEffect(() => {
    const initializeGoogleSignIn = () => {
      if (window.google) {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: handleCredentialResponse,
        });

        window.google.accounts.id.renderButton(
          document.getElementById("google-signin-button"),
          {
            theme: "outline",
            size: "large",
            width: 300,
            text: "signin_with",
            shape: "rectangular"
          }
        );
      }
    };

    const handleCredentialResponse = async (response) => {
      try {
        const result = await axios.post(`${API}/auth/google`, {
          token: response.credential
        });
        onSuccess(result.data);
      } catch (error) {
        console.error('Google auth error:', error);
        onError(error);
      }
    };

    if (!window.google) {
      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.onload = initializeGoogleSignIn;
      document.body.appendChild(script);
    } else {
      initializeGoogleSignIn();
    }
  }, [onSuccess, onError]);

  return <div id="google-signin-button"></div>;
};

// Mobile detection hook
const useIsMobile = () => {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkIfMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    checkIfMobile();
    window.addEventListener('resize', checkIfMobile);

    return () => window.removeEventListener('resize', checkIfMobile);
  }, []);

  return isMobile;
};

// Components
const Header = () => {
  const { user, logout, cart } = useDeviceContext();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [pendingChatsCount, setPendingChatsCount] = useState(0);
  const isMobile = useIsMobile();

  const cartItemsCount = cart.items?.reduce((total, item) => total + item.quantity, 0) || 0;

  useEffect(() => {
    if (user?.is_admin) {
      const loadPendingChats = async () => {
        try {
          const response = await axios.get(`${API}/admin/chat/sessions`);
          const pendingCount = response.data.filter(session => session.status === 'pending').length;
          setPendingChatsCount(pendingCount);
        } catch (error) {
          console.error('Error loading pending chats:', error);
        }
      };

      loadPendingChats();
      const interval = setInterval(loadPendingChats, 30000);
      return () => clearInterval(interval);
    }
  }, [user]);

  return (
    <header className="bg-gradient-to-r from-purple-900 via-black to-purple-900 text-white shadow-2xl border-b-2 border-purple-500 sticky top-0 z-50">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className={`${isMobile ? 'text-xl' : 'text-3xl'} font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent`}>
            🎁 {isMobile ? 'Mystery Box' : 'Mystery Box Store'}
          </Link>

          {isMobile && (
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="md:hidden p-2"
            >
              <div className="space-y-1">
                <div className={`w-6 h-0.5 bg-white transition-all ${isMenuOpen ? 'rotate-45 translate-y-1.5' : ''}`}></div>
                <div className={`w-6 h-0.5 bg-white transition-all ${isMenuOpen ? 'opacity-0' : ''}`}></div>
                <div className={`w-6 h-0.5 bg-white transition-all ${isMenuOpen ? '-rotate-45 -translate-y-1.5' : ''}`}></div>
              </div>
            </button>
          )}

          {!isMobile && (
            <nav className="hidden md:flex space-x-8">
              <Link to="/" className="hover:text-purple-300 transition-colors duration-300 flex items-center">
                🏠 Início
              </Link>
              <Link to="/produtos" className="hover:text-purple-300 transition-colors duration-300 flex items-center">
                📦 Produtos
              </Link>
              {user?.is_admin && (
                <Link to="/admin" className="hover:text-yellow-300 transition-colors duration-300 flex items-center relative">
                  ⚙️ Admin
                  {pendingChatsCount > 0 && (
                    <span className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs animate-pulse">
                      {pendingChatsCount}
                    </span>
                  )}
                </Link>
              )}
            </nav>
          )}

          {!isMobile && (
            <div className="flex items-center space-x-6">
              <Link to="/carrinho" className="relative hover:text-purple-300 transition-all duration-300 transform hover:scale-110">
                🛒 Carrinho
                {cartItemsCount > 0 && (
                  <span className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs animate-bounce">
                    {cartItemsCount}
                  </span>
                )}
              </Link>

              {user ? (
                <div className="flex items-center space-x-4">
                  {user.avatar_url && (
                    <img src={user.avatar_url} alt="Avatar" className="w-8 h-8 rounded-full" />
                  )}
                  <span className="text-purple-200">Olá, {user.name}</span>
                  <Link to="/perfil" className="text-purple-200 hover:text-purple-300 transition-colors duration-300">
                    👤 Perfil
                  </Link>
                  <button
                    onClick={logout}
                    className="text-sm hover:text-purple-300 transition-colors duration-300"
                  >
                    Sair
                  </button>
                </div>
              ) : (
                <Link to="/login" className="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg transition-all duration-300 transform hover:scale-105">
                  Entrar
                </Link>
              )}
            </div>
          )}

          {isMobile && (
            <div className="flex items-center space-x-3">
              <Link to="/carrinho" className="relative">
                <span className="text-2xl">🛒</span>
                {cartItemsCount > 0 && (
                  <span className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs animate-bounce">
                    {cartItemsCount}
                  </span>
                )}
              </Link>

              {user ? (
                <div className="flex items-center space-x-2">
                  {user.avatar_url && (
                    <img src={user.avatar_url} alt="Avatar" className="w-6 h-6 rounded-full" />
                  )}
                  <Link to="/perfil" className="text-xs text-purple-200 hover:text-purple-300">
                    👤
                  </Link>
                  <button
                    onClick={logout}
                    className="text-xs text-purple-200 hover:text-purple-300"
                  >
                    Sair
                  </button>
                </div>
              ) : (
                <Link to="/login" className="bg-purple-600 hover:bg-purple-700 px-3 py-1 rounded text-sm">
                  Entrar
                </Link>
              )}
            </div>
          )}
        </div>

        {isMobile && isMenuOpen && (
          <div className="md:hidden mt-4 pb-4 border-t border-purple-500/30">
            <nav className="flex flex-col space-y-3 mt-4">
              <Link to="/" className="hover:text-purple-300 transition-colors duration-300 flex items-center">
                🏠 Início
              </Link>
              <Link to="/produtos" className="hover:text-purple-300 transition-colors duration-300 flex items-center">
                📦 Produtos
              </Link>
              {user?.is_admin && (
                <Link to="/admin" className="hover:text-yellow-300 transition-colors duration-300 flex items-center relative">
                  ⚙️ Admin
                  {pendingChatsCount > 0 && (
                    <span className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs animate-pulse">
                      {pendingChatsCount}
                    </span>
                  )}
                </Link>
              )}
              <hr className="border-purple-500/30" />
              {user && (
                <Link to="/perfil" className="hover:text-purple-300 transition-colors duration-300 flex items-center">
                  👤 Perfil
                </Link>
              )}
            </nav>
          </div>
        )}
      </div>
    </header>
  );
};

const Home = () => {
  const [featuredProducts, setFeaturedProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const isMobile = useIsMobile();

  useEffect(() => {
    const loadData = async () => {
      try {
        const [productsRes, categoriesRes] = await Promise.all([
          axios.get(`${API}/products?featured=true`),
          axios.get(`${API}/categories`)
        ]);
        
        setFeaturedProducts(productsRes.data.slice(0, 3));
        setCategories(categoriesRes.data);
      } catch (error) {
        console.error('Error loading data:', error);
      }
    };
    loadData();
  }, []);

  return (
    <div className="min-h-screen mystery-gradient">
      {/* Hero Section */}
      <section className="relative mystery-gradient text-white py-20 md:py-32 overflow-hidden">
        <div className="absolute inset-0">
          <div className="stars"></div>
          <div className="moving-stars"></div>
        </div>
        <div className={`container mx-auto px-4 text-center relative z-10 ${isMobile ? 'py-8' : ''}`}>
          <h1 className={`hero-title ${isMobile ? 'text-4xl md:text-6xl' : 'text-6xl md:text-8xl'} font-bold mb-8`}>
            Descobre o Inesperado!
          </h1>
          <div className="text-4xl mb-4 animate-float">🎭 ⚡ 👻</div>
          <p className={`${isMobile ? 'text-lg mb-8' : 'text-2xl mb-12'} max-w-3xl mx-auto text-purple-200 leading-relaxed animate-fade-in-up`}>
            Mystery boxes temáticas cheias de surpresas incríveis.
            Mergulha no mistério e descobre tesouros únicos!
          </p>
          <div className={`${isMobile ? 'space-y-4' : 'space-x-6'} ${isMobile ? 'flex flex-col items-center' : ''} animate-fade-in-scale`}>
            <Link
              to="/produtos"
              className={`btn-mystery ${isMobile ? 'px-8 py-4 text-lg' : 'px-12 py-6 text-xl'} font-bold ${isMobile ? 'w-full max-w-xs' : ''}`}
            >
              🔍 Explorar Mistérios
            </Link>
          </div>
        </div>
      </section>

      {/* Featured Products */}
      <section className={`${isMobile ? 'py-12' : 'py-20'} glass-card mx-4 rounded-3xl my-8`}>
        <div className="container mx-auto px-4">
          <h2 className={`${isMobile ? 'text-3xl' : 'text-5xl'} font-bold text-center mb-12 text-white animate-fade-in-up`}>
            ✨ Mistérios em Destaque ✨
          </h2>

          <div className={`grid ${isMobile ? 'grid-cols-1 gap-6' : 'md:grid-cols-3 gap-10'}`}>
            {featuredProducts.map((product, index) => (
              <div key={product.id} className="mystery-box-card animate-fade-in-up" style={{animationDelay: `${index * 0.2}s`}}>
                <div className="product-image relative overflow-hidden">
                  <img
                    src={product.image_url}
                    alt={product.name}
                    className={`w-full ${isMobile ? 'h-48' : 'h-64'} object-cover transition-transform duration-500 hover:scale-110`}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-70"></div>
                  <div className="absolute top-4 right-4 animate-float">
                    <span className="text-2xl">✨</span>
                  </div>
                </div>
                <div className={`${isMobile ? 'p-6' : 'p-8'}`}>
                  <h3 className={`${isMobile ? 'text-lg' : 'text-2xl'} font-semibold mb-4 text-white`}>{product.name}</h3>
                  <p className="text-gray-300 mb-6 leading-relaxed line-clamp-3">{product.description}</p>
                  <div className="flex items-center justify-between">
                    <span className={`price-display ${isMobile ? 'text-2xl' : 'text-3xl'} font-bold`}>
                      €{product.price}
                    </span>
                    <Link
                      to={`/produto/${product.id}`}
                      className="btn-mystery"
                    >
                      🔮 Descobrir
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Categories */}
      <section className={`${isMobile ? 'py-12' : 'py-20'} glass-card mx-4 rounded-3xl my-8`}>
        <div className="container mx-auto px-4">
          <h2 className={`${isMobile ? 'text-3xl' : 'text-5xl'} font-bold text-center mb-12 text-white animate-fade-in-up`}>
            🎭 Universos Misteriosos 🎭
          </h2>

          <div className={`grid ${isMobile ? 'grid-cols-2 gap-4' : 'md:grid-cols-4 gap-8'}`}>
            {categories.map((category, index) => (
              <Link
                key={category.id}
                to="/produtos"
                className="category-card animate-fade-in-up"
                style={{animationDelay: `${index * 0.1}s`}}
              >
                <div className={`${isMobile ? 'text-3xl mb-2' : 'text-6xl mb-6'} animate-float`}
                     style={{animationDelay: `${index * 0.3}s`}}>
                  {category.emoji}
                </div>
                <h3 className={`${isMobile ? 'text-sm' : 'text-xl'} font-semibold text-white group-hover:text-purple-200 transition-colors duration-300`}>
                  {category.name}
                </h3>
                <p className={`text-gray-400 ${isMobile ? 'text-xs mt-1' : 'text-sm mt-2'} group-hover:text-purple-300 transition-colors duration-300`}>
                  {category.description}
                </p>
                <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                  <span className="text-yellow-400 animate-bounce">✨</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className={`${isMobile ? 'py-12' : 'py-20'} mystery-gradient text-center rounded-3xl mx-4 my-8 relative overflow-hidden`}>
        <div className="stars"></div>
        <div className="container mx-auto px-4 relative z-10">
          <h2 className={`hero-title ${isMobile ? 'text-3xl' : 'text-5xl'} font-bold mb-8`}>
            Pronto para a Aventura? 🚀
          </h2>
          <p className={`${isMobile ? 'text-lg mb-8' : 'text-xl mb-12'} text-purple-200 max-w-2xl mx-auto animate-fade-in-up`}>
            Junta-te a milhares de exploradores que já descobriram tesouros incríveis!
          </p>
          <Link
            to="/produtos"
            className={`btn-mystery ${isMobile ? 'px-8 py-4 text-lg' : 'px-12 py-6 text-xl'} font-bold animate-fade-in-scale`}
          >
            🎁 Começar Agora
          </Link>
        </div>
      </section>
    </div>
  );
};

const Products = () => {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { addToCart } = useDeviceContext();
  const isMobile = useIsMobile();

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const [productsRes, categoriesRes] = await Promise.all([
          axios.get(`${API}/products${selectedCategory ? `?category=${selectedCategory}` : ''}`),
          axios.get(`${API}/categories`)
        ]);
        
        setProducts(Array.isArray(productsRes.data) ? productsRes.data : []);
        setCategories(Array.isArray(categoriesRes.data) ? categoriesRes.data : []);
      } catch (error) {
        console.error('Error loading products:', error);
        setError(error.message);
        setProducts([]);
        setCategories([]);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [selectedCategory]);

  const handleAddToCart = async (productId) => {
    const success = await addToCart(productId);
    if (success) {
      const button = document.querySelector(`[data-product-id="${productId}"]`);
      if (button) {
        button.classList.add('animate-pulse');
        setTimeout(() => button.classList.remove('animate-pulse'), 1000);
      }
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
        <div className="container mx-auto px-4 py-12">
          <div className="text-center text-white">
            <div className="animate-spin text-6xl mb-4">🔮</div>
            <p className="text-xl">Carregando produtos...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
        <div className="container mx-auto px-4 py-12">
          <div className="text-center text-white">
            <div className="text-6xl mb-4">⚠️</div>
            <p className="text-xl mb-4">Erro ao carregar produtos</p>
            <p className="text-gray-300">{error}</p>
            <button 
              onClick={() => window.location.reload()} 
              className="mt-4 bg-purple-600 hover:bg-purple-700 px-6 py-2 rounded-lg transition-colors"
            >
              Tentar novamente
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen mystery-gradient">
      <div className="container mx-auto px-4 py-12">
        <h1 className={`hero-title ${isMobile ? 'text-3xl' : 'text-5xl'} font-bold mb-12 text-center animate-fade-in-up`}>
          🔮 Nossos Mistérios 🔮
        </h1>

        {/* Category Filter */}
        <div className="mb-12 text-center animate-fade-in-scale">
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className={`form-input ${isMobile ? 'w-full max-w-xs' : 'px-6 py-3 text-lg'} focus:outline-none transition-all duration-300`}
          >
            <option value="">🎭 Todos os Universos</option>
            {categories.map(category => (
              <option key={category.id} value={category.id}>
                {category.emoji} {category.name}
              </option>
            ))}
          </select>
        </div>

        {/* Products Grid */}
        {products.length === 0 ? (
          <div className="text-center text-white glass-card p-12 rounded-3xl animate-fade-in-scale">
            <div className="text-6xl mb-4 animate-float">📦</div>
            <h2 className="text-2xl font-bold mb-4">Nenhum produto encontrado</h2>
            <p className="text-gray-300 mb-6">Tenta uma categoria diferente ou volta mais tarde!</p>
            <Link to="/" className="btn-mystery">
              🏠 Voltar ao Início
            </Link>
          </div>
        ) : (
          <div className="grid-auto-fit">
            {products.map((product, index) => (
              <div key={product.id} className="mystery-box-card animate-fade-in-up" style={{animationDelay: `${index * 0.1}s`}}>
                <div className="product-image relative overflow-hidden">
                  <img
                    src={product.image_url}
                    alt={product.name}
                    className={`w-full ${isMobile ? 'h-40' : 'h-48'} object-cover transition-transform duration-500 hover:scale-110`}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-70"></div>
                  {product.featured && (
                    <div className="absolute top-3 right-3 bg-gradient-to-r from-yellow-400 to-orange-500 text-black px-3 py-1 rounded-full text-xs font-bold animate-pulse shadow-lg">
                      ⭐ Destaque
                    </div>
                  )}
                </div>
                <div className={`${isMobile ? 'p-4' : 'p-6'}`}>
                  <h3 className={`${isMobile ? 'text-base' : 'text-lg'} font-semibold mb-3 text-white`}>{product.name}</h3>
                  <p className={`text-gray-300 ${isMobile ? 'text-sm' : 'text-sm'} mb-4 line-clamp-3`}>{product.description}</p>

                  <div className="mb-4">
                    <div className="flex items-center justify-between">
                      <span className={`price-display ${isMobile ? 'text-lg' : 'text-2xl'} font-bold`}>
                        €{product.price}
                      </span>
                      <span className="text-xs text-gray-400 bg-gray-700 px-2 py-1 rounded-full">avulsa</span>
                    </div>

                    {product.subscription_prices && product.subscription_prices['12_months'] && (
                      <div className="mt-2 text-xs text-green-400 bg-green-900/20 border border-green-500/30 rounded-lg p-2">
                        💎 Assinatura: desde €{product.subscription_prices['12_months']}/mês
                        <span className="text-yellow-400 ml-1 font-semibold">(-20% desconto!)</span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center justify-between space-x-2">
                    <Link
                      to={`/produto/${product.id}`}
                      className="btn-mystery flex-1 text-center"
                    >
                      🔮 Descobrir
                    </Link>
                    <button
                      onClick={() => handleAddToCart(product.id)}
                      data-product-id={product.id}
                      className={`bg-gray-700 hover:bg-gray-600 text-white ${isMobile ? 'px-3 py-2 text-sm' : 'px-4 py-2'} rounded-lg transition-all duration-300 transform hover:scale-105 border border-gray-600 hover:border-purple-400`}
                      title="Adicionar ao carrinho"
                    >
                      🛒
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const ProductDetail = () => {
  const { id } = useParams();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSubscription, setSelectedSubscription] = useState(null);
  const { addToCart } = useDeviceContext();
  const isMobile = useIsMobile();

  useEffect(() => {
    const loadProduct = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${API}/products/${id}`);
        setProduct(response.data);
      } catch (error) {
        console.error('Error loading product:', error);
        setError(error.message);
      } finally {
        setLoading(false);
      }
    };
    loadProduct();
  }, [id]);

  const handleAddToCart = async () => {
    const success = await addToCart(id, 1, selectedSubscription);
    if (success) {
      alert('Produto adicionado ao carrinho!');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
        <div className="container mx-auto px-4 py-12">
          <div className="text-center text-white">
            <div className="animate-spin text-6xl mb-4">🔮</div>
            <p className="text-xl">Carregando produto...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
        <div className="container mx-auto px-4 py-12">
          <div className="text-center text-white">
            <div className="text-6xl mb-4">⚠️</div>
            <p className="text-xl mb-4">Produto não encontrado</p>
            <Link to="/produtos" className="bg-purple-600 hover:bg-purple-700 px-6 py-2 rounded-lg transition-colors">
              Voltar aos produtos
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <div className={`grid ${isMobile ? 'grid-cols-1 gap-8' : 'md:grid-cols-2 gap-12'}`}>
          {/* Product Image */}
          <div className="relative">
            <img
              src={product.image_url}
              alt={product.name}
              className="w-full h-96 object-cover rounded-2xl shadow-2xl"
            />
            {product.featured && (
              <div className="absolute top-4 right-4 bg-yellow-500 text-black px-3 py-1 rounded-full text-sm font-bold animate-pulse">
                ⭐ Produto em Destaque
              </div>
            )}
          </div>

          {/* Product Info */}
          <div className="text-white">
            <h1 className={`${isMobile ? 'text-3xl' : 'text-5xl'} font-bold mb-6 bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent`}>
              {product.name}
            </h1>
            
            <p className="text-xl text-gray-300 mb-8 leading-relaxed">
              {product.description}
            </p>

            {/* Pricing Options */}
            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">💰 Opções de Compra</h3>
              
              {/* One-time purchase */}
              <div className="mb-4">
                <label className="flex items-center p-4 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-700 transition-colors">
                  <input
                    type="radio"
                    name="purchase-type"
                    value="one-time"
                    checked={selectedSubscription === null}
                    onChange={() => setSelectedSubscription(null)}
                    className="mr-3"
                  />
                  <div className="flex-1">
                    <div className="font-semibold">Compra Avulsa</div>
                    <div className="text-2xl font-bold text-purple-400">€{product.price}</div>
                  </div>
                </label>
              </div>

              {/* Subscription options */}
              {product.subscription_prices && (
                <>
                  {Object.entries(product.subscription_prices).map(([duration, price]) => {
                    const months = parseInt(duration.split('_')[0]);
                    const discount = months === 3 ? 10 : months === 6 ? 15 : 20;
                    const totalPrice = price * months;
                    const originalPrice = product.price * months;
                    const savings = originalPrice - totalPrice;

                    return (
                      <div key={duration} className="mb-4">
                        <label className="flex items-center p-4 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-700 transition-colors">
                          <input
                            type="radio"
                            name="purchase-type"
                            value={duration}
                            checked={selectedSubscription === duration}
                            onChange={() => setSelectedSubscription(duration)}
                            className="mr-3"
                          />
                          <div className="flex-1">
                            <div className="font-semibold">Assinatura {months} meses</div>
                            <div className="text-2xl font-bold text-green-400">€{price}/mês</div>
                            <div className="text-sm text-gray-400">
                              Total: €{totalPrice} | Poupas €{savings.toFixed(2)} ({discount}% desconto)
                            </div>
                          </div>
                          <div className="text-yellow-400 font-bold">-{discount}%</div>
                        </label>
                      </div>
                    );
                  })}
                </>
              )}
            </div>

            {/* Add to Cart Button */}
            <button
              onClick={handleAddToCart}
              className={`w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white ${isMobile ? 'py-4 text-lg' : 'py-6 text-xl'} rounded-xl font-bold hover:from-purple-700 hover:to-pink-700 transition-all duration-300 transform hover:scale-105 shadow-2xl`}
            >
              🛒 Adicionar ao Carrinho
            </button>

            {/* Back to Products */}
            <Link
              to="/produtos"
              className="block text-center mt-6 text-purple-300 hover:text-purple-200 transition-colors"
            >
              ← Voltar aos produtos
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

const Cart = () => {
  const { cart, removeFromCart, applyCoupon, removeCoupon, loadCart } = useDeviceContext();
  const [couponCode, setCouponCode] = useState('');
  const [couponMessage, setCouponMessage] = useState('');
  const isMobile = useIsMobile();
  const navigate = useNavigate();

  useEffect(() => {
    loadCart();
  }, []);

  const handleApplyCoupon = async () => {
    const result = await applyCoupon(couponCode);
    if (result.success) {
      setCouponMessage('Cupão aplicado com sucesso!');
      setCouponCode('');
    } else {
      setCouponMessage(result.error);
    }
    setTimeout(() => setCouponMessage(''), 3000);
  };

  const handleRemoveCoupon = async () => {
    await removeCoupon();
    setCouponMessage('Cupão removido');
    setTimeout(() => setCouponMessage(''), 3000);
  };

  if (!cart.items || cart.items.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
        <div className="container mx-auto px-4 py-12">
          <div className="text-center text-white">
            <div className="text-6xl mb-4">🛒</div>
            <h1 className="text-3xl font-bold mb-4">Carrinho Vazio</h1>
            <p className="text-gray-300 mb-8">Adiciona alguns produtos misteriosos!</p>
            <Link
              to="/produtos"
              className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-8 py-4 rounded-xl font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-300 transform hover:scale-105"
            >
              🔍 Explorar Produtos
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <h1 className={`${isMobile ? 'text-3xl' : 'text-5xl'} font-bold mb-12 text-center text-white`}>
          🛒 Seu Carrinho Mágico
        </h1>

        <div className={`grid ${isMobile ? 'grid-cols-1 gap-8' : 'lg:grid-cols-3 gap-12'}`}>
          {/* Cart Items */}
          <div className={`${isMobile ? '' : 'lg:col-span-2'}`}>
            {cart.items.map((item, index) => (
              <div key={index} className="bg-gray-800 rounded-xl p-6 mb-6 shadow-2xl">
                <div className="flex items-center space-x-4">
                  <img
                    src={item.product.image_url}
                    alt={item.product.name}
                    className="w-20 h-20 object-cover rounded-lg"
                  />
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold text-white">{item.product.name}</h3>
                    <p className="text-gray-300">Quantidade: {item.quantity}</p>
                    {item.subscription_type && (
                      <p className="text-green-400">Assinatura: {item.subscription_type.replace('_', ' ')}</p>
                    )}
                    <p className="text-2xl font-bold text-purple-400">€{item.total_price}</p>
                  </div>
                  <button
                    onClick={() => removeFromCart(item.product.id, item.subscription_type)}
                    className="text-red-400 hover:text-red-300 text-2xl transition-colors"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Cart Summary */}
          <div className="bg-gray-800 rounded-xl p-6 h-fit shadow-2xl">
            <h3 className="text-2xl font-bold text-white mb-6">Resumo do Pedido</h3>
            
            {/* Coupon Section */}
            <div className="mb-6">
              <label className="block text-white mb-2">Cupão de Desconto</label>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={couponCode}
                  onChange={(e) => setCouponCode(e.target.value)}
                  placeholder="Código do cupão"
                  className="flex-1 bg-gray-700 text-white px-3 py-2 rounded-lg border border-gray-600 focus:outline-none focus:border-purple-400"
                />
                <button
                  onClick={handleApplyCoupon}
                  className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors"
                >
                  Aplicar
                </button>
              </div>
              {cart.coupon && (
                <div className="mt-2 flex items-center justify-between text-green-400">
                  <span>Cupão: {cart.coupon.code}</span>
                  <button onClick={handleRemoveCoupon} className="text-red-400 hover:text-red-300">
                    ❌
                  </button>
                </div>
              )}
              {couponMessage && (
                <p className="mt-2 text-sm text-yellow-400">{couponMessage}</p>
              )}
            </div>

            {/* Price Breakdown */}
            <div className="space-y-3 mb-6">
              <div className="flex justify-between text-white">
                <span>Subtotal:</span>
                <span>€{cart.subtotal}</span>
              </div>
              {cart.discount > 0 && (
                <div className="flex justify-between text-green-400">
                  <span>Desconto:</span>
                  <span>-€{cart.discount}</span>
                </div>
              )}
              <div className="border-t border-gray-600 pt-3">
                <div className="flex justify-between text-2xl font-bold text-purple-400">
                  <span>Total:</span>
                  <span>€{cart.total}</span>
                </div>
              </div>
            </div>

            {/* Checkout Button */}
            <button
              onClick={() => navigate('/checkout')}
              className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-4 rounded-xl font-bold hover:from-purple-700 hover:to-pink-700 transition-all duration-300 transform hover:scale-105 shadow-2xl"
            >
              🚀 Finalizar Compra
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const Login = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [nif, setNif] = useState('');
  const [birthDate, setBirthDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useDeviceContext();
  const navigate = useNavigate();
  const isMobile = useIsMobile();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (isLogin) {
        const response = await axios.post(`${API}/auth/login`, {
          email,
          password
        });
        login(response.data.access_token, response.data.user);
        navigate('/');
      } else {
        const response = await axios.post(`${API}/auth/register`, {
          email,
          password,
          name,
          phone,
          address,
          nif,
          birth_date: birthDate
        });
        login(response.data.access_token, response.data.user);
        navigate('/');
      }
    } catch (error) {
      setError(error.response?.data?.detail || 'Erro na autenticação');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSuccess = (data) => {
    login(data.access_token, data.user);
    navigate('/');
  };

  const handleGoogleError = (error) => {
    setError('Erro no login com Google');
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <div className="max-w-md mx-auto">
          <div className="bg-gray-800 rounded-2xl shadow-2xl p-8">
            <h1 className="text-3xl font-bold text-center text-white mb-8">
              {isLogin ? '🔑 Entrar' : '📝 Registar'}
            </h1>

            {error && (
              <div className="bg-red-600 text-white p-3 rounded-lg mb-6">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              {!isLogin && (
                <div>
                  <label className="block text-white mb-2">Nome</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    className="w-full bg-gray-700 text-white px-4 py-3 rounded-lg border border-gray-600 focus:outline-none focus:border-purple-400"
                  />
                </div>
              )}

              <div>
                <label className="block text-white mb-2">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full bg-gray-700 text-white px-4 py-3 rounded-lg border border-gray-600 focus:outline-none focus:border-purple-400"
                />
              </div>

              <div>
                <label className="block text-white mb-2">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full bg-gray-700 text-white px-4 py-3 rounded-lg border border-gray-600 focus:outline-none focus:border-purple-400"
                />
              </div>

              {!isLogin && (
                <>
                  <div>
                    <label className="block text-white mb-2">Telefone</label>
                    <input
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      className="w-full bg-gray-700 text-white px-4 py-3 rounded-lg border border-gray-600 focus:outline-none focus:border-purple-400"
                    />
                  </div>

                  <div>
                    <label className="block text-white mb-2">Morada</label>
                    <input
                      type="text"
                      value={address}
                      onChange={(e) => setAddress(e.target.value)}
                      className="w-full bg-gray-700 text-white px-4 py-3 rounded-lg border border-gray-600 focus:outline-none focus:border-purple-400"
                    />
                  </div>

                  <div>
                    <label className="block text-white mb-2">NIF</label>
                    <input
                      type="text"
                      value={nif}
                      onChange={(e) => setNif(e.target.value)}
                      className="w-full bg-gray-700 text-white px-4 py-3 rounded-lg border border-gray-600 focus:outline-none focus:border-purple-400"
                    />
                  </div>

                  <div>
                    <label className="block text-white mb-2">Data de Nascimento</label>
                    <input
                      type="date"
                      value={birthDate}
                      onChange={(e) => setBirthDate(e.target.value)}
                      className="w-full bg-gray-700 text-white px-4 py-3 rounded-lg border border-gray-600 focus:outline-none focus:border-purple-400"
                    />
                  </div>
                </>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-3 rounded-lg font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-300 transform hover:scale-105 disabled:opacity-50"
              >
                {loading ? '⏳ Aguarde...' : (isLogin ? '🔑 Entrar' : '📝 Registar')}
              </button>
            </form>

            {isLogin && GOOGLE_CLIENT_ID && (
              <div className="mt-6">
                <div className="text-center text-gray-400 mb-4">ou</div>
                <GoogleLoginButton
                  onSuccess={handleGoogleSuccess}
                  onError={handleGoogleError}
                />
              </div>
            )}

            <div className="mt-6 text-center">
              <button
                onClick={() => setIsLogin(!isLogin)}
                className="text-purple-400 hover:text-purple-300 transition-colors"
              >
                {isLogin ? 'Não tens conta? Registar' : 'Já tens conta? Entrar'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const AdminDashboard = () => {
  const { user } = useDeviceContext();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const isMobile = useIsMobile();

  useEffect(() => {
    if (!user?.is_admin) {
      navigate('/');
      return;
    }

    const loadStats = async () => {
      try {
        const response = await axios.get(`${API}/admin/dashboard`);
        setStats(response.data);
      } catch (error) {
        console.error('Error loading admin stats:', error);
      } finally {
        setLoading(false);
      }
    };

    loadStats();
  }, [user, navigate]);

  if (!user?.is_admin) {
    return null;
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
        <div className="container mx-auto px-4 py-12">
          <div className="text-center text-white">
            <div className="animate-spin text-6xl mb-4">⚙️</div>
            <p className="text-xl">Carregando dashboard...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <h1 className={`${isMobile ? 'text-3xl' : 'text-5xl'} font-bold mb-12 text-center text-white`}>
          ⚙️ Painel de Administração
        </h1>

        {/* Quick Stats */}
        {stats && (
          <div className={`grid ${isMobile ? 'grid-cols-2 gap-4' : 'md:grid-cols-4 gap-6'} mb-12`}>
            <div className="bg-gray-800 rounded-xl p-6 text-center">
              <div className="text-3xl mb-2">👥</div>
              <div className="text-2xl font-bold text-white">{stats.total_users}</div>
              <div className="text-gray-400">Utilizadores</div>
            </div>
            <div className="bg-gray-800 rounded-xl p-6 text-center">
              <div className="text-3xl mb-2">📦</div>
              <div className="text-2xl font-bold text-white">{stats.total_products}</div>
              <div className="text-gray-400">Produtos</div>
            </div>
            <div className="bg-gray-800 rounded-xl p-6 text-center">
              <div className="text-3xl mb-2">🛒</div>
              <div className="text-2xl font-bold text-white">{stats.total_orders}</div>
              <div className="text-gray-400">Pedidos</div>
            </div>
            <div className="bg-gray-800 rounded-xl p-6 text-center">
              <div className="text-3xl mb-2">💰</div>
              <div className="text-2xl font-bold text-white">€{stats.total_revenue}</div>
              <div className="text-gray-400">Receita</div>
            </div>
          </div>
        )}

        {/* Admin Menu */}
        <div className={`grid ${isMobile ? 'grid-cols-1 gap-4' : 'md:grid-cols-3 lg:grid-cols-4 gap-6'}`}>
          <Link
            to="/admin/orders"
            className="bg-gray-800 hover:bg-gray-700 rounded-xl p-6 text-center transition-all duration-300 transform hover:scale-105"
          >
            <div className="text-4xl mb-4">📋</div>
            <h3 className="text-xl font-semibold text-white">Pedidos</h3>
            <p className="text-gray-400">Gerir pedidos</p>
          </Link>

          <Link
            to="/admin/products"
            className="bg-gray-800 hover:bg-gray-700 rounded-xl p-6 text-center transition-all duration-300 transform hover:scale-105"
          >
            <div className="text-4xl mb-4">📦</div>
            <h3 className="text-xl font-semibold text-white">Produtos</h3>
            <p className="text-gray-400">Gerir produtos</p>
          </Link>

          <Link
            to="/admin/coupons"
            className="bg-gray-800 hover:bg-gray-700 rounded-xl p-6 text-center transition-all duration-300 transform hover:scale-105"
          >
            <div className="text-4xl mb-4">🎫</div>
            <h3 className="text-xl font-semibold text-white">Cupões</h3>
            <p className="text-gray-400">Gerir cupões</p>
          </Link>

          <Link
            to="/admin/categories"
            className="bg-gray-800 hover:bg-gray-700 rounded-xl p-6 text-center transition-all duration-300 transform hover:scale-105"
          >
            <div className="text-4xl mb-4">🏷️</div>
            <h3 className="text-xl font-semibold text-white">Categorias</h3>
            <p className="text-gray-400">Gerir categorias</p>
          </Link>

          <Link
            to="/admin/emails"
            className="bg-gray-800 hover:bg-gray-700 rounded-xl p-6 text-center transition-all duration-300 transform hover:scale-105"
          >
            <div className="text-4xl mb-4">📧</div>
            <h3 className="text-xl font-semibold text-white">Emails</h3>
            <p className="text-gray-400">Enviar emails</p>
          </Link>

          <div className="bg-gray-800 rounded-xl p-6 text-center">
            <div className="text-4xl mb-4">👥</div>
            <h3 className="text-xl font-semibold text-white">Utilizadores</h3>
            <p className="text-gray-400">Em breve</p>
          </div>
        </div>
      </div>
    </div>
  );
};

const UserProfile = () => {
  const { user, logout } = useDeviceContext();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const isMobile = useIsMobile();

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }

    const loadOrders = async () => {
      try {
        const response = await axios.get(`${API}/auth/orders`);
        setOrders(response.data);
      } catch (error) {
        console.error('Error loading orders:', error);
      } finally {
        setLoading(false);
      }
    };

    loadOrders();
  }, [user, navigate]);

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <h1 className={`${isMobile ? 'text-3xl' : 'text-5xl'} font-bold mb-12 text-center text-white`}>
          👤 Meu Perfil
        </h1>

        <div className={`grid ${isMobile ? 'grid-cols-1 gap-8' : 'lg:grid-cols-3 gap-12'}`}>
          {/* User Info */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-2xl font-bold text-white mb-6">Informações Pessoais</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-gray-400 mb-1">Nome</label>
                <div className="text-white">{user.name}</div>
              </div>
              <div>
                <label className="block text-gray-400 mb-1">Email</label>
                <div className="text-white">{user.email}</div>
              </div>
              {user.phone && (
                <div>
                  <label className="block text-gray-400 mb-1">Telefone</label>
                  <div className="text-white">{user.phone}</div>
                </div>
              )}
              {user.address && (
                <div>
                  <label className="block text-gray-400 mb-1">Morada</label>
                  <div className="text-white">{user.address}</div>
                </div>
              )}
            </div>

            <button
              onClick={logout}
              className="w-full mt-6 bg-red-600 hover:bg-red-700 text-white py-3 rounded-lg transition-colors"
            >
              🚪 Sair da Conta
            </button>
          </div>

          {/* Order History */}
          <div className={`${isMobile ? '' : 'lg:col-span-2'}`}>
            <div className="bg-gray-800 rounded-xl p-6">
              <h2 className="text-2xl font-bold text-white mb-6">Histórico de Pedidos</h2>
              
              {loading ? (
                <div className="text-center text-white">
                  <div className="animate-spin text-4xl mb-4">🔄</div>
                  <p>Carregando pedidos...</p>
                </div>
              ) : orders.length === 0 ? (
                <div className="text-center text-gray-400">
                  <div className="text-4xl mb-4">📦</div>
                  <p>Nenhum pedido encontrado</p>
                  <Link
                    to="/produtos"
                    className="inline-block mt-4 bg-purple-600 hover:bg-purple-700 text-white px-6 py-2 rounded-lg transition-colors"
                  >
                    Fazer primeira compra
                  </Link>
                </div>
              ) : (
                <div className="space-y-4">
                  {orders.map((order) => (
                    <div key={order.id} className="bg-gray-700 rounded-lg p-4">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <h3 className="font-semibold text-white">Pedido #{order.id}</h3>
                          <p className="text-gray-400 text-sm">
                            {new Date(order.created_at).toLocaleDateString('pt-PT')}
                          </p>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold text-purple-400">€{order.total_amount}</div>
                          <div className={`text-sm px-2 py-1 rounded ${
                            order.status === 'delivered' ? 'bg-green-600' :
                            order.status === 'shipped' ? 'bg-blue-600' :
                            order.status === 'cancelled' ? 'bg-red-600' :
                            'bg-yellow-600'
                          }`}>
                            {order.status}
                          </div>
                        </div>
                      </div>
                      <div className="text-gray-300 text-sm">
                        {order.items.map((item, index) => (
                          <div key={index}>
                            {item.product.name} x{item.quantity}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const App = () => {
  return (
    <DeviceProvider>
      <div className="App min-h-screen bg-gray-900">
        <BrowserRouter>
          <Header />
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/produtos" element={<Products />} />
            <Route path="/produto/:id" element={<ProductDetail />} />
            <Route path="/carrinho" element={<Cart />} />
            <Route path="/login" element={<Login />} />
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/perfil" element={<UserProfile />} />
          </Routes>
        </BrowserRouter>
      </div>
    </DeviceProvider>
  );
};

export default App;