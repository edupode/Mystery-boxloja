import React, { useState, useEffect, useCallback, useMemo, memo, createContext, useContext, Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import LazyLoad from 'react-lazyload';
import { useInView } from 'react-intersection-observer';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

console.log('App.js - Environment loaded:');
console.log('REACT_APP_BACKEND_URL:', process.env.REACT_APP_BACKEND_URL);
console.log('BACKEND_URL:', BACKEND_URL);
console.log('API:', API);

// Performance utilities
const useDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

// Local storage cache utilities
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

const cacheUtils = {
  set: (key, data) => {
    const cacheItem = {
      data,
      timestamp: Date.now()
    };
    localStorage.setItem(`cache_${key}`, JSON.stringify(cacheItem));
  },
  
  get: (key) => {
    try {
      const cacheItem = JSON.parse(localStorage.getItem(`cache_${key}`));
      if (!cacheItem) return null;
      
      const isExpired = Date.now() - cacheItem.timestamp > CACHE_DURATION;
      if (isExpired) {
        localStorage.removeItem(`cache_${key}`);
        return null;
      }
      
      return cacheItem.data;
    } catch {
      return null;
    }
  },
  
  clear: (pattern) => {
    const keys = Object.keys(localStorage);
    keys.forEach(key => {
      if (key.startsWith(`cache_${pattern}`)) {
        localStorage.removeItem(key);
      }
    });
  }
};

// Image optimization component
const OptimizedImage = memo(({ src, alt, className, loading = "lazy", placeholder = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjE4IiBmaWxsPSIjYWFhIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+aW1hZ2VtPC90ZXh0Pjwvc3ZnPg==" }) => {
  const [imageSrc, setImageSrc] = useState(placeholder);
  const [imageRef, inView] = useInView({
    triggerOnce: true,
    threshold: 0.1
  });

  useEffect(() => {
    if (inView && src) {
      setImageSrc(src);
    }
  }, [inView, src]);

  return (
    <img
      ref={imageRef}
      src={imageSrc}
      alt={alt}
      className={className}
      loading={loading}
      style={{ transition: 'opacity 0.3s ease' }}
    />
  );
});
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
      // Verify token and get user info
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

    // Send first ping immediately
    keepAlive();

    // Set up interval to ping every 10 minutes (600,000 ms)
    const intervalId = setInterval(keepAlive, 10 * 60 * 1000);

    // Cleanup interval on component unmount
    return () => clearInterval(intervalId);
  }, []);

  const fetchUserInfo = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      // Token is invalid, remove it
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

    // Load Google Identity Services
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

  // Load pending chats count for admins
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
      // Update count every 30 seconds
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

          {/* Mobile Menu Button */}
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

          {/* Desktop Navigation */}
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

          {/* Desktop User Actions */}
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

          {/* Mobile User Actions - Now includes login button */}
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

        {/* Mobile Menu */}
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
        console.log('Loading data - API URL:', API);
        console.log('Backend URL:', BACKEND_URL);
        
        const [productsRes, categoriesRes] = await Promise.all([
          axios.get(`${API}/products?featured=true`),
          axios.get(`${API}/categories`)
        ]);
        
        console.log('Products response:', productsRes.data);
        console.log('Categories response:', categoriesRes.data);
        
        setFeaturedProducts(productsRes.data.slice(0, 3));
        setCategories(categoriesRes.data);
      } catch (error) {
        console.error('Error loading data:', error);
        console.error('Error details:', error.response || error.message);
      }
    };
    loadData();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      {/* Hero Section */}
      <section className="relative bg-gradient-to-r from-purple-900 via-black to-red-900 text-white py-20 md:py-32 overflow-hidden">
        <div className="absolute inset-0 bg-black opacity-50"></div>
        <div className="absolute inset-0">
          <div className="stars"></div>
          <div className="moving-stars"></div>
        </div>
        <div className={`container mx-auto px-4 text-center relative z-10 ${isMobile ? 'py-8' : ''}`}>
          <h1 className={`${isMobile ? 'text-4xl md:text-6xl' : 'text-6xl md:text-8xl'} font-bold mb-8 animate-pulse bg-gradient-to-r from-purple-400 via-pink-400 to-red-400 bg-clip-text text-transparent`}>
            Descobre o Inesperado!
          </h1>
          <div className="text-4xl mb-4 animate-bounce">🎭 ⚡ 👻</div>
          <p className={`${isMobile ? 'text-lg mb-8' : 'text-2xl mb-12'} max-w-3xl mx-auto text-purple-200 leading-relaxed`}>
            Mystery boxes temáticas cheias de surpresas incríveis.
            Mergulha no mistério e descobre tesouros únicos!
          </p>
          <div className={`${isMobile ? 'space-y-4' : 'space-x-6'} ${isMobile ? 'flex flex-col items-center' : ''}`}>
            <Link
              to="/produtos"
              className={`bg-gradient-to-r from-purple-600 to-pink-600 text-white ${isMobile ? 'px-8 py-3' : 'px-10 py-4'} rounded-xl font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-300 transform hover:scale-110 shadow-2xl ${isMobile ? 'w-full max-w-xs text-center' : ''}`}
            >
              🔍 Explorar Mistérios
            </Link>
          </div>
        </div>
      </section>

      {/* Featured Products */}
      <section className={`${isMobile ? 'py-12' : 'py-20'} bg-gradient-to-b from-black to-purple-900`}>
        <div className="container mx-auto px-4">
          <h2 className={`${isMobile ? 'text-3xl' : 'text-5xl'} font-bold text-center mb-12 text-white`}>
            ✨ Mistérios em Destaque ✨
          </h2>

          <div className={`grid ${isMobile ? 'grid-cols-1 gap-6' : 'md:grid-cols-3 gap-10'}`}>
            {featuredProducts.map((product, index) => (
              <div key={product.id} className={`mystery-box-card hover:shadow-purple-500/50 transition-all duration-500 transform hover:scale-105 animate-fade-in-up`} style={{animationDelay: `${index * 0.2}s`}}>
                <div className="relative overflow-hidden">
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
                <div className={`${isMobile ? 'p-6' : 'p-8'} bg-gradient-to-b from-gray-800 to-gray-900`}>
                  <h3 className={`${isMobile ? 'text-lg' : 'text-2xl'} font-semibold mb-4 text-white`}>{product.name}</h3>
                  <p className="text-gray-300 mb-6 leading-relaxed">{product.description}</p>
                  <div className="flex items-center justify-between">
                    <span className={`${isMobile ? 'text-2xl' : 'text-3xl'} font-bold text-purple-400 animate-pulse-glow`}>
                      €{product.price}
                    </span>
                    <Link
                      to={`/produto/${product.id}`}
                      className={`btn-mystery bg-gradient-to-r from-purple-600 to-pink-600 text-white ${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all duration-300 transform hover:scale-105`}
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
      <section className={`${isMobile ? 'py-12' : 'py-20'} bg-gradient-to-b from-purple-900 to-black`}>
        <div className="container mx-auto px-4">
          <h2 className={`${isMobile ? 'text-3xl' : 'text-5xl'} font-bold text-center mb-12 text-white`}>
            🎭 Universos Misteriosos 🎭
          </h2>

          <div className={`grid ${isMobile ? 'grid-cols-2 gap-4' : 'md:grid-cols-4 gap-8'}`}>
            {categories.map((category, index) => (
              <Link
                key={category.id}
                to={`/categoria/${category.id}`}
                className={`group relative bg-gradient-to-br from-gray-800 to-gray-900 rounded-2xl ${isMobile ? 'p-4' : 'p-8'} text-center hover:from-purple-800 hover:to-pink-800 transition-all duration-500 transform hover:scale-110 hover:rotate-2 border border-purple-500/30 hover:border-purple-400 animate-fade-in-up`}
                style={{animationDelay: `${index * 0.1}s`}}
              >
                <div className={`${isMobile ? 'text-3xl mb-2' : 'text-6xl mb-6'} animate-float group-hover:animate-spin transition-all duration-500`}
                     style={{animationDelay: `${index * 0.3}s`}}>
                  {category.emoji}
                </div>
                <h3 className={`${isMobile ? 'text-sm' : 'text-xl'} font-semibold text-white group-hover:text-purple-200 transition-colors duration-300`}>
                  {category.name}
                </h3>
                <p className={`text-gray-400 ${isMobile ? 'text-xs mt-1' : 'text-sm mt-2'} group-hover:text-purple-300 transition-colors duration-300`}>
                  {category.description}
                </p>
                <div className="absolute inset-0 bg-gradient-to-r from-purple-600/20 to-pink-600/20 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                  <span className="text-yellow-400 animate-bounce">✨</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className={`${isMobile ? 'py-12' : 'py-20'} bg-gradient-to-r from-purple-900 via-black to-red-900 text-center`}>
        <div className="container mx-auto px-4">
          <h2 className={`${isMobile ? 'text-3xl' : 'text-5xl'} font-bold mb-8 text-white`}>
            Pronto para a Aventura? 🚀
          </h2>
          <p className={`${isMobile ? 'text-lg mb-8' : 'text-xl mb-12'} text-purple-200 max-w-2xl mx-auto`}>
            Junta-te a milhares de exploradores que já descobriram tesouros incríveis!
          </p>
          <Link
            to="/produtos"
            className={`bg-gradient-to-r from-yellow-500 to-orange-500 text-black ${isMobile ? 'px-8 py-4 text-lg' : 'px-12 py-6 text-xl'} rounded-2xl font-bold hover:from-yellow-600 hover:to-orange-600 transition-all duration-300 transform hover:scale-110 shadow-2xl`}
          >
            🎁 Começar Agora
          </Link>
        </div>
      </section>
    </div>
  );
};

const Products = memo(() => {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('');
  const { addToCart } = useDeviceContext();
  const isMobile = useIsMobile();

  useEffect(() => {
    const loadData = async () => {
      try {
        console.log('Products - Loading data - API URL:', API);
        console.log('Products - Selected category:', selectedCategory);
        
        // Try cache first
        const cacheKey = `products_${selectedCategory || 'all'}`;
        const cachedProducts = cacheUtils.get(cacheKey);
        const cachedCategories = cacheUtils.get('categories');
        
        if (cachedProducts && cachedCategories) {
          console.log('Products - Using cached data');
          setProducts(cachedProducts);
          setCategories(cachedCategories);
          return;
        }

        console.log('Products - Fetching from API');
        const [productsRes, categoriesRes] = await Promise.all([
          axios.get(`${API}/products${selectedCategory ? `?category=${selectedCategory}` : ''}`),
          axios.get(`${API}/categories`)
        ]);
        
        console.log('Products - API response:', productsRes.data);
        console.log('Categories - API response:', categoriesRes.data);
        
        setProducts(productsRes.data);
        setCategories(categoriesRes.data);
        
        // Cache the results
        cacheUtils.set(cacheKey, productsRes.data);
        cacheUtils.set('categories', categoriesRes.data);
      } catch (error) {
        console.error('Error loading products:', error);
      }
    };
    loadData();
  }, [selectedCategory]);

  const handleAddToCart = async (productId) => {
    const success = await addToCart(productId);
    if (success) {
      // Show success animation
      const button = document.querySelector(`[data-product-id="${productId}"]`);
      if (button) {
        button.classList.add('animate-pulse');
        setTimeout(() => button.classList.remove('animate-pulse'), 1000);
      }
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <h1 className={`${isMobile ? 'text-3xl' : 'text-5xl'} font-bold mb-12 text-center text-white`}>
          🔮 Nossos Mistérios 🔮
        </h1>

        {/* Category Filter */}
        <div className="mb-12 text-center">
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className={`bg-gray-800 text-white border border-purple-500 rounded-lg ${isMobile ? 'px-4 py-2 text-base w-full max-w-xs' : 'px-6 py-3 text-lg'} focus:outline-none focus:border-purple-400 transition-colors duration-300`}
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
        <div className={`grid ${isMobile ? 'grid-cols-1 gap-6' : 'md:grid-cols-3 lg:grid-cols-4 gap-8'}`}>
          {products.map((product, index) => (
            <div key={product.id} className="mystery-box-card hover:shadow-purple-500/50 transition-all duration-500 animate-fade-in-up" style={{animationDelay: `${index * 0.1}s`}}>
              <div className="relative overflow-hidden">
                <img
                  src={product.image_url}
                  alt={product.name}
                  className={`w-full ${isMobile ? 'h-40' : 'h-48'} object-cover transition-transform duration-500 hover:scale-110`}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-70"></div>
                {product.featured && (
                  <div className="absolute top-2 right-2 bg-yellow-500 text-black px-2 py-1 rounded-full text-xs font-bold animate-pulse">
                    ⭐ Destaque
                  </div>
                )}
              </div>
              <div className={`${isMobile ? 'p-4' : 'p-6'} bg-gradient-to-b from-gray-800 to-gray-900`}>
                <h3 className={`${isMobile ? 'text-base' : 'text-lg'} font-semibold mb-3 text-white`}>{product.name}</h3>
                <p className={`text-gray-300 ${isMobile ? 'text-sm' : 'text-sm'} mb-4 line-clamp-3`}>{product.description}</p>
                
                <div className="mb-3">
                  <div className="flex items-center justify-between">
                    <span className={`${isMobile ? 'text-lg' : 'text-2xl'} font-bold text-purple-400`}>
                      €{product.price}
                    </span>
                    <span className="text-xs text-gray-400">avulsa</span>
                  </div>
                  
                  {/* Subscription pricing hint */}
                  {product.subscription_prices && product.subscription_prices['12_months'] && (
                    <div className="mt-2 text-xs text-green-400">
                      Assinatura: desde €{product.subscription_prices['12_months']}/mês
                      <span className="text-yellow-400 ml-1">(-20% desconto!)</span>
                    </div>
                  )}
                </div>
                
                <div className="flex items-center justify-between space-x-2">
                  <Link
                    to={`/produto/${product.id}`}
                    className={`flex-1 bg-gradient-to-r from-purple-600 to-pink-600 text-white ${isMobile ? 'px-3 py-2 text-sm' : 'px-4 py-2'} rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all duration-300 transform hover:scale-105 text-center`}
                  >
                    🔮 Descobrir
                  </Link>
                  <button
                    onClick={() => handleAddToCart(product.id)}
                    data-product-id={product.id}
                    className={`bg-gray-700 hover:bg-gray-600 text-white ${isMobile ? 'px-3 py-2 text-sm' : 'px-4 py-2'} rounded-lg transition-all duration-300 transform hover:scale-105`}
                  >
                    🛒
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
});

const ProductDetail = () => {
  const location = useLocation();
  const id = location.pathname.split('/').pop();
  const [product, setProduct] = useState(null);
  const [selectedSubscription, setSelectedSubscription] = useState('');
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const { addToCart } = useDeviceContext();
  const isMobile = useIsMobile();

  useEffect(() => {
    const loadProduct = async () => {
      try {
        const response = await axios.get(`${API}/products/${id}`);
        setProduct(response.data);
      } catch (error) {
        console.error('Error loading product:', error);
      }
    };
    loadProduct();
    
    // Scroll to top when component loads (fixes the "discover" button issue)
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [id]);

  const handleAddToCart = async () => {
    const success = await addToCart(product.id, 1, selectedSubscription || null);
    if (success) {
      alert('🎉 Produto adicionado ao carrinho!');
    }
  };

  if (!product) return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black flex items-center justify-center">
      <div className="text-white text-center">
        <div className="animate-spin text-6xl mb-4">🔮</div>
        <p className="text-xl">Carregando mistério...</p>
      </div>
    </div>
  );

  const currentPrice = selectedSubscription
    ? product.subscription_prices[selectedSubscription]
    : product.price;

  // Create array of all images (primary + gallery) with robust handling
  const allImages = (() => {
    const images = [];
    
    // Add primary image if exists
    if (product.image_url) {
      images.push(product.image_url);
    }
    
    // Add gallery images if exists and is an array
    if (product.images) {
      if (Array.isArray(product.images)) {
        images.push(...product.images.filter(Boolean));
      } else if (typeof product.images === 'string' && product.images.trim()) {
        // Handle case where images might be a single string
        images.push(product.images);
      }
    }
    
    return images.filter(Boolean);
  })();

  const nextImage = () => {
    setCurrentImageIndex((prev) => (prev + 1) % allImages.length);
  };

  const prevImage = () => {
    setCurrentImageIndex((prev) => (prev - 1 + allImages.length) % allImages.length);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <div className={`grid ${isMobile ? 'grid-cols-1 gap-8' : 'md:grid-cols-2 gap-12'}`}>
          {/* Image Gallery Section */}
          <div className="relative">
            {/* Main Image */}
            <div className="relative group">
              <img
                src={allImages[currentImageIndex]}
                alt={product.name}
                className="w-full h-96 object-cover rounded-2xl shadow-2xl transform hover:scale-105 transition-transform duration-500"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent rounded-2xl"></div>
              
              {/* Navigation Arrows */}
              {allImages.length > 1 && (
                <>
                  <button
                    onClick={prevImage}
                    className="absolute left-4 top-1/2 transform -translate-y-1/2 bg-black/50 hover:bg-black/70 text-white p-3 rounded-full transition-all duration-300 opacity-0 group-hover:opacity-100"
                  >
                    ←
                  </button>
                  <button
                    onClick={nextImage}
                    className="absolute right-4 top-1/2 transform -translate-y-1/2 bg-black/50 hover:bg-black/70 text-white p-3 rounded-full transition-all duration-300 opacity-0 group-hover:opacity-100"
                  >
                    →
                  </button>
                </>
              )}
              
              {/* Image Counter */}
              {allImages.length > 1 && (
                <div className="absolute bottom-4 right-4 bg-black/70 text-white px-3 py-1 rounded-full text-sm">
                  {currentImageIndex + 1} / {allImages.length}
                </div>
              )}
            </div>
            
            {/* Thumbnail Gallery */}
            {allImages.length > 1 && (
              <div className="flex gap-2 mt-4 overflow-x-auto pb-2">
                {allImages.map((image, index) => (
                  <button
                    key={index}
                    onClick={() => setCurrentImageIndex(index)}
                    className={`flex-shrink-0 w-20 h-20 rounded-lg overflow-hidden border-2 transition-all duration-300 ${
                      index === currentImageIndex 
                        ? 'border-purple-400 opacity-100' 
                        : 'border-gray-600 opacity-60 hover:opacity-80'
                    }`}
                  >
                    <img
                      src={image}
                      alt={`${product.name} ${index + 1}`}
                      className="w-full h-full object-cover"
                    />
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="text-white">
            <h1 className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold mb-6 bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent`}>
              {product.name}
            </h1>
            <p className={`text-gray-300 mb-8 ${isMobile ? 'text-base' : 'text-lg'} leading-relaxed`}>{product.description}</p>

            <div className="mb-8 bg-gray-800/50 rounded-2xl p-6 border border-purple-500/30">
              <h3 className={`${isMobile ? 'text-lg' : 'text-2xl'} font-semibold mb-6 text-purple-300`}>🎯 Opções de Compra:</h3>

              <div className="space-y-4">
                <label className="flex items-center p-4 rounded-lg bg-gray-700/50 hover:bg-gray-700 transition-colors duration-300 cursor-pointer">
                  <input
                    type="radio"
                    name="purchaseType"
                    value=""
                    checked={selectedSubscription === ''}
                    onChange={(e) => setSelectedSubscription('')}
                    className="mr-4 scale-125"
                  />
                  <span className={`${isMobile ? 'text-base' : 'text-lg'}`}>🛒 Compra avulsa - €{product.price}</span>
                </label>

                <div className="ml-6 space-y-3">
                  <h4 className={`${isMobile ? 'text-base' : 'text-lg'} font-semibold text-purple-300`}>📅 Assinaturas (com desconto!):</h4>

                  {Object.entries(product.subscription_prices).map(([key, price]) => {
                    const months = parseInt(key.replace('_months', ''));
                    const discount = ((product.price - price) / product.price * 100).toFixed(0);
                    const totalPrice = price * months;
                    const originalTotal = product.price * months;
                    const savings = originalTotal - totalPrice;
                    
                    return (
                      <label key={key} className="flex items-center p-4 rounded-lg bg-gray-700/30 hover:bg-gray-700/50 transition-colors duration-300 cursor-pointer border-l-4 border-purple-500/30">
                        <input
                          type="radio"
                          name="purchaseType"
                          value={key}
                          checked={selectedSubscription === key}
                          onChange={(e) => setSelectedSubscription(e.target.value)}
                          className="mr-4 scale-125"
                        />
                        <div className="flex-1">
                          <div className="flex items-center justify-between mb-2">
                            <span className={`${isMobile ? 'text-base' : 'text-lg'} font-semibold text-white`}>
                              Assinatura {months} meses
                            </span>
                            <div className="text-right">
                              <span className="text-gray-400 line-through text-sm">€{originalTotal.toFixed(2)}</span>
                              <span className="text-purple-400 font-bold ml-2">€{totalPrice.toFixed(2)}</span>
                            </div>
                          </div>
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-gray-300">€{price}/mês</span>
                            <div className="flex items-center space-x-2">
                              <span className="text-green-400 font-semibold">-{discount}% desconto</span>
                              <span className="text-green-400">Poupa €{savings.toFixed(2)}</span>
                            </div>
                          </div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="mb-8 text-center">
              <span className={`${isMobile ? 'text-3xl' : 'text-5xl'} font-bold text-purple-400`}>
                €{currentPrice}
                {selectedSubscription && <span className={`${isMobile ? 'text-lg' : 'text-2xl'} text-gray-400`}>/mês</span>}
              </span>
            </div>

            <button
              onClick={handleAddToCart}
              className={`w-full bg-gradient-to-r from-purple-600 via-pink-600 to-red-600 text-white ${isMobile ? 'py-3 text-lg' : 'py-4 text-xl'} rounded-2xl font-bold hover:from-purple-700 hover:via-pink-700 hover:to-red-700 transition-all duration-300 transform hover:scale-105 shadow-2xl`}
            >
              🎁 Adicionar ao Carrinho
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const Cart = () => {
  const { cart, removeFromCart, sessionId, applyCoupon, removeCoupon } = useDeviceContext();
  const [products, setProducts] = useState({});
  const [shippingMethods, setShippingMethods] = useState([]);
  const [couponCode, setCouponCode] = useState('');
  const [couponMessage, setCouponMessage] = useState('');
  const [isApplyingCoupon, setIsApplyingCoupon] = useState(false);
  const navigate = useNavigate();
  const isMobile = useIsMobile();

  useEffect(() => {
    const loadData = async () => {
      try {
        const [shippingRes] = await Promise.all([
          axios.get(`${API}/shipping-methods`)
        ]);
        setShippingMethods(shippingRes.data);
      } catch (error) {
        console.error('Error loading shipping methods:', error);
      }
    };
    loadData();

    if (cart.items?.length > 0) {
      const loadProducts = async () => {
        const productMap = {};
        for (const item of cart.items) {
          if (!productMap[item.product_id]) {
            try {
              const response = await axios.get(`${API}/products/${item.product_id}`);
              productMap[item.product_id] = response.data;
            } catch (error) {
              console.error('Error loading product:', error);
            }
          }
        }
        setProducts(productMap);
      };
      loadProducts();
    }
  }, [cart]);

  const calculateSubtotal = () => {
    return cart.items?.reduce((total, item) => {
      const product = products[item.product_id];
      if (!product) return total;

      const price = item.subscription_type
        ? product.subscription_prices[item.subscription_type]
        : product.price;

      return total + (price * item.quantity);
    }, 0) || 0;
  };

  const handleApplyCoupon = async () => {
    if (!couponCode.trim()) return;
    
    setIsApplyingCoupon(true);
    setCouponMessage('');
    
    const result = await applyCoupon(couponCode.trim());
    
    if (result.success) {
      setCouponMessage('✅ Cupão aplicado com sucesso!');
      setCouponCode('');
    } else {
      setCouponMessage(`❌ ${result.error}`);
    }
    
    setIsApplyingCoupon(false);
  };

  const handleRemoveCoupon = async () => {
    await removeCoupon();
    setCouponMessage('');
  };

  const subtotal = calculateSubtotal();
  const vat = subtotal * 0.23;
  const shippingCost = 3.99; // Default shipping
  const total = subtotal + vat + shippingCost;

  if (!cart.items || cart.items.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black flex items-center justify-center">
        <div className="text-center text-white px-4">
          <div className="text-8xl mb-8 animate-bounce">🛒</div>
          <h1 className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold mb-6`}>Seu Carrinho está Vazio</h1>
          <p className={`${isMobile ? 'text-lg' : 'text-xl'} text-gray-400 mb-8`}>Que tal explorar nossos mistérios?</p>
          <Link
            to="/produtos"
            className={`bg-gradient-to-r from-purple-600 to-pink-600 text-white ${isMobile ? 'px-6 py-3' : 'px-8 py-4'} rounded-xl font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-300 transform hover:scale-105`}
          >
            🔍 Descobrir Produtos
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <h1 className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold mb-12 text-center text-white`}>
          🛒 Seu Carrinho Misterioso
        </h1>

        <div className={`grid ${isMobile ? 'grid-cols-1 gap-8' : 'lg:grid-cols-3 gap-12'}`}>
          <div className={`${isMobile ? '' : 'lg:col-span-2'} space-y-6`}>
            {cart.items.map((item, index) => {
              const product = products[item.product_id];
              if (!product) return null;

              const price = item.subscription_type
                ? product.subscription_prices[item.subscription_type]
                : product.price;

              return (
                <div key={index} className="bg-gray-800/50 rounded-2xl p-6 border border-purple-500/30 hover:border-purple-400 transition-colors duration-300">
                  <div className={`flex ${isMobile ? 'flex-col space-y-4' : 'items-center'}`}>
                    <img
                      src={product.image_url}
                      alt={product.name}
                      className={`${isMobile ? 'w-full h-32' : 'w-24 h-24'} object-cover rounded-lg ${isMobile ? '' : 'mr-6'}`}
                    />
                    <div className="flex-1">
                      <h3 className={`${isMobile ? 'text-lg' : 'text-xl'} font-semibold text-white mb-2`}>{product.name}</h3>
                      {item.subscription_type && (
                        <p className="text-purple-400 mb-1">
                          📅 Assinatura: {item.subscription_type.replace('_', ' ')}
                        </p>
                      )}
                      <p className="text-gray-400">Quantidade: {item.quantity}</p>
                    </div>
                    <div className={`${isMobile ? 'flex justify-between items-center' : 'text-right'}`}>
                      <p className={`${isMobile ? 'text-xl' : 'text-2xl'} font-bold text-purple-400`}>€{(price * item.quantity).toFixed(2)}</p>
                      <button
                        onClick={() => removeFromCart(item.product_id, item.subscription_type)}
                        className="text-red-400 text-sm hover:text-red-300 mt-2 transition-colors duration-300"
                      >
                        🗑️ Remover
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Coupon Section */}
            <div className="bg-gray-800/50 rounded-2xl p-6 border border-purple-500/30">
              <h3 className={`${isMobile ? 'text-lg' : 'text-xl'} font-semibold mb-4 text-white`}>🎫 Cupão de Desconto</h3>
              
              {cart.coupon_code ? (
                <div className="flex items-center justify-between bg-green-900/30 border border-green-500/50 rounded-lg p-4">
                  <div>
                    <p className="text-green-400 font-semibold">✅ Cupão aplicado: {cart.coupon_code}</p>
                  </div>
                  <button
                    onClick={handleRemoveCoupon}
                    className="text-red-400 hover:text-red-300 text-sm"
                  >
                    🗑️ Remover
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className={`flex ${isMobile ? 'flex-col space-y-2' : 'space-x-3'}`}>
                    <input
                      type="text"
                      value={couponCode}
                      onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                      placeholder="Digite o código do cupão"
                      className={`${isMobile ? 'w-full' : 'flex-1'} bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none`}
                    />
                    <button
                      onClick={handleApplyCoupon}
                      disabled={isApplyingCoupon || !couponCode.trim()}
                      className={`${isMobile ? 'w-full' : ''} bg-gradient-to-r from-green-600 to-green-700 text-white px-6 py-3 rounded-lg hover:from-green-700 hover:to-green-800 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed`}
                    >
                      {isApplyingCoupon ? 'Aplicando...' : '🎫 Aplicar'}
                    </button>
                  </div>
                  {couponMessage && (
                    <p className={`text-sm ${couponMessage.includes('✅') ? 'text-green-400' : 'text-red-400'}`}>
                      {couponMessage}
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="bg-gray-800/50 rounded-2xl p-8 border border-purple-500/30 h-fit">
            <h3 className={`${isMobile ? 'text-lg' : 'text-2xl'} font-semibold mb-6 text-white`}>💰 Resumo do Pedido</h3>

            <div className="space-y-4 mb-6">
              <div className="flex justify-between text-gray-300">
                <span>Subtotal:</span>
                <span>€{subtotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-gray-300">
                <span>IVA (23%):</span>
                <span>€{vat.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-gray-300">
                <span>Envio:</span>
                <span>€{shippingCost.toFixed(2)}</span>
              </div>
              <hr className="border-purple-500/30" />
              <div className={`flex justify-between font-bold ${isMobile ? 'text-lg' : 'text-xl'} text-purple-400`}>
                <span>Total:</span>
                <span>€{total.toFixed(2)}</span>
              </div>
            </div>

            <button
              onClick={() => navigate('/checkout')}
              className={`w-full bg-gradient-to-r from-purple-600 via-pink-600 to-red-600 text-white ${isMobile ? 'py-3 text-base' : 'py-4 text-lg'} rounded-xl font-bold hover:from-purple-700 hover:via-pink-700 hover:to-red-700 transition-all duration-300 transform hover:scale-105 shadow-2xl`}
            >
              🚀 Finalizar Compra
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const Checkout = () => {
  const { cart, sessionId } = useDeviceContext();
  const [formData, setFormData] = useState({
    street: '',
    postalCode: '',
    city: '',
    phone: '',
    nif: '',
    paymentMethod: 'stripe',
    shippingMethod: 'standard'
  });
  const [shippingMethods, setShippingMethods] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [nifError, setNifError] = useState('');
  const navigate = useNavigate();
  const isMobile = useIsMobile();

  useEffect(() => {
    const loadShippingMethods = async () => {
      try {
        const response = await axios.get(`${API}/shipping-methods`);
        setShippingMethods(response.data);
      } catch (error) {
        console.error('Error loading shipping methods:', error);
      }
    };
    loadShippingMethods();
  }, []);

  const validateNIF = (nif) => {
    if (!nif) return true; // NIF is optional
    
    if (!nif.startsWith('PT')) {
      return false;
    }
    
    const nifNumbers = nif.slice(2);
    if (!/^\d{9}$/.test(nifNumbers)) {
      return false;
    }
    
    // Validate check digit
    const digits = nifNumbers.slice(0, 8).split('').map(Number);
    const checkSum = digits.reduce((sum, digit, index) => sum + digit * (9 - index), 0);
    const remainder = checkSum % 11;
    const checkDigit = remainder < 2 ? 0 : 11 - remainder;
    
    return parseInt(nifNumbers[8]) === checkDigit;
  };

  const handleNIFChange = (value) => {
    let formattedNIF = value.toUpperCase();
    
    // Auto-add PT prefix if not present and user starts typing numbers
    if (formattedNIF && !formattedNIF.startsWith('PT') && /^\d/.test(formattedNIF)) {
      formattedNIF = 'PT' + formattedNIF;
    }
    
    setFormData({...formData, nif: formattedNIF});
    
    if (formattedNIF && !validateNIF(formattedNIF)) {
      setNifError('NIF inválido. Deve começar com PT seguido de 9 dígitos válidos');
    } else {
      setNifError('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (formData.nif && !validateNIF(formData.nif)) {
      setNifError('NIF inválido. Deve começar com PT seguido de 9 dígitos válidos');
      return;
    }
    
    setIsLoading(true);

    try {
      const response = await axios.post(`${API}/checkout`, {
        cart_id: sessionId,
        shipping_address: `${formData.street}, ${formData.postalCode} ${formData.city}`,
        phone: formData.phone,
        nif: formData.nif || null,
        payment_method: formData.paymentMethod,
        shipping_method: formData.shippingMethod,
        origin_url: window.location.origin
      });

      if (response.data.checkout_url) {
        window.location.href = response.data.checkout_url;
      } else {
        navigate(`/order-success/${response.data.order_id}`);
      }
    } catch (error) {
      console.error('Checkout error:', error);
      alert('❌ Erro no checkout. Tente novamente.');
    }

    setIsLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <h1 className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold mb-12 text-center text-white`}>
          🚀 Finalizar Compra
        </h1>

        <form onSubmit={handleSubmit} className={`max-w-3xl mx-auto ${isMobile ? 'space-y-6' : ''}`}>
          <div className="bg-gray-800/50 rounded-2xl p-8 mb-8 border border-purple-500/30">
            <h3 className={`${isMobile ? 'text-lg' : 'text-2xl'} font-semibold mb-6 text-white`}>📍 Informações de Entrega</h3>

            <div className="mb-6">
              <label className={`block ${isMobile ? 'text-base' : 'text-lg'} font-medium mb-3 text-gray-300`}>Endereço *</label>
              <input
                type="text"
                value={formData.street}
                onChange={(e) => setFormData({...formData, street: e.target.value})}
                required
                className={`w-full border border-purple-500/30 rounded-lg px-4 py-3 bg-gray-700 text-white focus:border-purple-400 focus:outline-none transition-colors duration-300`}
                placeholder="Rua e número da porta"
              />
            </div>

            <div className={`grid ${isMobile ? 'grid-cols-1 gap-4' : 'md:grid-cols-2 gap-6'} mb-6`}>
              <div>
                <label className={`block ${isMobile ? 'text-base' : 'text-lg'} font-medium mb-3 text-gray-300`}>Código Postal *</label>
                <input
                  type="text"
                  value={formData.postalCode}
                  onChange={(e) => {
                    const value = e.target.value.replace(/[^\d-]/g, ''); // Only digits and dash
                    if (value.length <= 8) { // Max length for XXXX-XXX format
                      let formatted = value;
                      if (value.length > 4 && !value.includes('-')) {
                        formatted = value.slice(0, 4) + '-' + value.slice(4);
                      }
                      setFormData({...formData, postalCode: formatted});
                    }
                  }}
                  required
                  className={`w-full border border-purple-500/30 rounded-lg px-4 py-3 bg-gray-700 text-white focus:border-purple-400 focus:outline-none transition-colors duration-300`}
                  placeholder="1234-567"
                  maxLength="8"
                />
              </div>
              <div>
                <label className={`block ${isMobile ? 'text-base' : 'text-lg'} font-medium mb-3 text-gray-300`}>Localidade *</label>
                <input
                  type="text"
                  value={formData.city}
                  onChange={(e) => setFormData({...formData, city: e.target.value})}
                  required
                  className={`w-full border border-purple-500/30 rounded-lg px-4 py-3 bg-gray-700 text-white focus:border-purple-400 focus:outline-none transition-colors duration-300`}
                  placeholder="Lisboa"
                />
              </div>
            </div>

            <div className="mb-6">
              <label className={`block ${isMobile ? 'text-base' : 'text-lg'} font-medium mb-3 text-gray-300`}>Número de Telemóvel *</label>
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({...formData, phone: e.target.value})}
                required
                className="w-full border border-purple-500/30 rounded-lg px-4 py-3 bg-gray-700 text-white focus:border-purple-400 focus:outline-none transition-colors duration-300"
                placeholder="+351 xxx xxx xxx"
              />
            </div>

            <div className="mb-6">
              <label className={`block ${isMobile ? 'text-base' : 'text-lg'} font-medium mb-3 text-gray-300`}>NIF (Opcional)</label>
              <input
                type="text"
                value={formData.nif}
                onChange={(e) => handleNIFChange(e.target.value)}
                className={`w-full border ${nifError ? 'border-red-500' : 'border-purple-500/30'} rounded-lg px-4 py-3 bg-gray-700 text-white focus:border-purple-400 focus:outline-none transition-colors duration-300`}
                placeholder="PT123456789"
                maxLength={11}
              />
              {nifError && (
                <p className="text-red-400 text-sm mt-2">{nifError}</p>
              )}
              <p className="text-gray-400 text-sm mt-2">
                Digite PT seguido de 9 dígitos (ex: PT123456789). Campo opcional.
              </p>
            </div>
          </div>

          <div className="bg-gray-800/50 rounded-2xl p-8 mb-8 border border-purple-500/30">
            <h3 className={`${isMobile ? 'text-lg' : 'text-2xl'} font-semibold mb-6 text-white`}>🚚 Método de Envio</h3>

            <div className="space-y-4">
              {shippingMethods.map(method => (
                <label key={method.id} className="flex items-center p-4 rounded-lg bg-gray-700/50 hover:bg-gray-700 transition-colors duration-300 cursor-pointer">
                  <input
                    type="radio"
                    name="shippingMethod"
                    value={method.id}
                    checked={formData.shippingMethod === method.id}
                    onChange={(e) => setFormData({...formData, shippingMethod: e.target.value})}
                    className="mr-4 scale-125"
                  />
                  <span className="flex-1 text-white">{method.name}</span>
                  <span className="text-purple-400 font-semibold">
                    {method.price === 0 ? 'Grátis' : `€${method.price}`}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div className="bg-gray-800/50 rounded-2xl p-8 mb-8 border border-purple-500/30">
            <h3 className={`${isMobile ? 'text-lg' : 'text-2xl'} font-semibold mb-6 text-white`}>💳 Método de Pagamento</h3>

            <div className="space-y-4">
              <label className="flex items-center p-4 rounded-lg bg-gray-700/50 hover:bg-gray-700 transition-colors duration-300 cursor-pointer">
                <input
                  type="radio"
                  name="paymentMethod"
                  value="stripe"
                  checked={formData.paymentMethod === 'stripe'}
                  onChange={(e) => setFormData({...formData, paymentMethod: e.target.value})}
                  className="mr-4 scale-125"
                />
                <span className="text-white">💳 Stripe (Cartão/Klarna/Multibanco/Etc...)</span>
              </label>
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading || nifError}
            className={`w-full bg-gradient-to-r from-purple-600 via-pink-600 to-red-600 text-white ${isMobile ? 'py-4 text-lg' : 'py-6 text-xl'} rounded-2xl font-bold hover:from-purple-700 hover:via-pink-700 hover:to-red-700 transition-all duration-300 transform hover:scale-105 shadow-2xl disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {isLoading ? (
              <span className="flex items-center justify-center">
                <div className="animate-spin mr-3">🔮</div>
                Processando...
              </span>
            ) : (
              '🎁 Confirmar Pedido'
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

const Success = () => {
  const [paymentStatus, setPaymentStatus] = useState('checking');
  const location = useLocation();
  const isMobile = useIsMobile();

  useEffect(() => {
    const checkPaymentStatus = async () => {
      const urlParams = new URLSearchParams(location.search);
      const sessionId = urlParams.get('session_id');

      if (!sessionId) {
        setPaymentStatus('error');
        return;
      }

      try {
        const response = await axios.get(`${API}/payments/checkout/status/${sessionId}`);

        if (response.data.payment_status === 'paid') {
          setPaymentStatus('success');
        } else {
          setTimeout(checkPaymentStatus, 2000);
        }
      } catch (error) {
        console.error('Error checking payment status:', error);
        setPaymentStatus('error');
      }
    };

    checkPaymentStatus();
  }, [location]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black flex items-center justify-center">
      <div className={`text-center text-white max-w-2xl mx-auto px-4`}>
        {paymentStatus === 'checking' && (
          <div>
            <div className="text-8xl mb-8 animate-spin">🔮</div>
            <h1 className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold mb-4`}>Verificando Pagamento...</h1>
            <p className={`${isMobile ? 'text-lg' : 'text-xl'} text-gray-400`}>Por favor aguarde enquanto confirmamos o seu pagamento.</p>
          </div>
        )}

        {paymentStatus === 'success' && (
          <div>
            <div className="text-8xl mb-8 animate-bounce">🎉</div>
            <h1 className={`${isMobile ? 'text-3xl' : 'text-5xl'} font-bold text-green-400 mb-6`}>Pagamento Confirmado!</h1>
            <p className={`${isMobile ? 'text-lg mb-6' : 'text-xl mb-8'} text-gray-300`}>
              Obrigado pela sua compra! O seu mistério está a caminho.
              Receberá em breve um email de confirmação com os detalhes do envio.
            </p>
            <div className={`${isMobile ? 'space-y-4' : 'space-x-4'} ${isMobile ? 'flex flex-col items-center' : ''}`}>
              <Link
                to="/"
                className={`bg-gradient-to-r from-purple-600 to-pink-600 text-white ${isMobile ? 'px-6 py-3 w-full max-w-xs' : 'px-8 py-4'} rounded-xl font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-300 transform hover:scale-105`}
              >
                🏠 Voltar ao Início
              </Link>
              <Link
                to="/produtos"
                className={`border-2 border-purple-400 text-purple-300 ${isMobile ? 'px-6 py-3 w-full max-w-xs' : 'px-8 py-4'} rounded-xl font-semibold hover:bg-purple-600 hover:text-white transition-all duration-300 transform hover:scale-105`}
              >
                🔍 Mais Mistérios
              </Link>
            </div>
          </div>
        )}

        {paymentStatus === 'error' && (
          <div>
            <div className="text-8xl mb-8">❌</div>
            <h1 className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold text-red-400 mb-6`}>Erro no Pagamento</h1>
            <p className={`${isMobile ? 'text-lg mb-6' : 'text-xl mb-8'} text-gray-400`}>
              Ocorreu um erro no processamento do pagamento. Por favor, tente novamente.
            </p>
            <Link
              to="/carrinho"
              className={`bg-gradient-to-r from-purple-600 to-pink-600 text-white ${isMobile ? 'px-6 py-3' : 'px-8 py-4'} rounded-xl font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-300 transform hover:scale-105`}
            >
              🛒 Voltar ao Carrinho
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};

const Login = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useDeviceContext();
  const navigate = useNavigate();
  const isMobile = useIsMobile();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const response = await axios.post(`${API}${endpoint}`, formData);

      if (response.data.access_token) {
        login(response.data.access_token, response.data.user);
        navigate('/');
      }
    } catch (error) {
      alert(error.response?.data?.detail || 'Erro no sistema');
    }

    setIsLoading(false);
  };

  const handleGoogleSuccess = (tokenData) => {
    login(tokenData.access_token, tokenData.user);
    navigate('/');
  };

  const handleGoogleError = (error) => {
    console.error('Google login error:', error);
    alert('Erro no login com Google');
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black flex items-center justify-center">
      <div className={`${isMobile ? 'max-w-sm' : 'max-w-md'} mx-auto bg-gray-800/50 rounded-2xl shadow-2xl p-8 border border-purple-500/30 ${isMobile ? 'mx-4' : ''}`}>
        <div className="text-center mb-8">
          <div className="text-6xl mb-4">🔮</div>
          <h1 className={`${isMobile ? 'text-2xl' : 'text-3xl'} font-bold text-white mb-2`}>
            {isLogin ? 'Entrar' : 'Criar Conta'}
          </h1>
          <p className="text-gray-400">Junte-se aos exploradores de mistérios!</p>
        </div>

        {/* Google Login */}
        <div className="mb-6">
          <GoogleLoginButton
            onSuccess={handleGoogleSuccess}
            onError={handleGoogleError}
          />
        </div>

        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-600"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-gray-800 text-gray-400">ou</span>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          {!isLogin && (
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2 text-gray-300">Nome</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                required={!isLogin}
                className="w-full border border-purple-500/30 rounded-lg px-4 py-3 bg-gray-700 text-white focus:border-purple-400 focus:outline-none transition-colors duration-300"
                placeholder="Seu nome completo"
              />
            </div>
          )}

          <div className="mb-4">
            <label className="block text-sm font-medium mb-2 text-gray-300">Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              required
              className="w-full border border-purple-500/30 rounded-lg px-4 py-3 bg-gray-700 text-white focus:border-purple-400 focus:outline-none transition-colors duration-300"
              placeholder="seu@email.com"
            />
          </div>

          <div className="mb-6">
            <label className="block text-sm font-medium mb-2 text-gray-300">Senha</label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              required
              className="w-full border border-purple-500/30 rounded-lg px-4 py-3 bg-gray-700 text-white focus:border-purple-400 focus:outline-none transition-colors duration-300"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-3 rounded-lg font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-300 transform hover:scale-105 disabled:opacity-50"
          >
            {isLoading ? (
              <span className="flex items-center justify-center">
                <div className="animate-spin mr-2">🔮</div>
                Processando...
              </span>
            ) : (
              isLogin ? '🚀 Entrar' : '✨ Criar Conta'
            )}
          </button>
        </form>

        <p className="text-center mt-6 text-gray-400">
          {isLogin ? 'Não tem conta?' : 'Já tem conta?'}
          <button
            onClick={() => setIsLogin(!isLogin)}
            className="text-purple-400 hover:text-purple-300 ml-2 font-semibold transition-colors duration-300"
          >
            {isLogin ? 'Criar conta' : 'Fazer login'}
          </button>
        </p>
      </div>
    </div>
  );
};

// Admin Components
const AdminDashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [users, setUsers] = useState([]);
  const [newAdmin, setNewAdmin] = useState({ email: '', name: '' });
  const [coupons, setCoupons] = useState([]);
  const [promotions, setPromotions] = useState([]);
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [passwordModalUser, setPasswordModalUser] = useState(null);
  const [newPassword, setNewPassword] = useState('');
  const [pendingChatsCount, setPendingChatsCount] = useState(0);
  const { user } = useDeviceContext();
  const isMobile = useIsMobile();

  useEffect(() => {
    if (user?.is_admin) {
      loadDashboardData();
      loadUsers();
      loadCoupons();
      loadPromotions();
      loadPendingChats();
      // Update pending chats count every 30 seconds
      const interval = setInterval(loadPendingChats, 30000);
      return () => clearInterval(interval);
    }
  }, [user]);

  const loadPendingChats = async () => {
    try {
      const response = await axios.get(`${API}/admin/chat/sessions`);
      const pendingCount = response.data.filter(session => session.status === 'pending').length;
      setPendingChatsCount(pendingCount);
    } catch (error) {
      console.error('Error loading pending chats:', error);
    }
  };

  const loadDashboardData = async () => {
    try {
      const response = await axios.get(`${API}/admin/dashboard`);
      setDashboardData(response.data);
    } catch (error) {
      console.error('Error loading dashboard:', error);
    }
  };

  const loadUsers = async () => {
    try {
      const response = await axios.get(`${API}/admin/users`);
      setUsers(response.data);
    } catch (error) {
      console.error('Error loading users:', error);
    }
  };

  const loadCoupons = async () => {
    try {
      const response = await axios.get(`${API}/admin/coupons`);
      setCoupons(response.data);
    } catch (error) {
      console.error('Error loading coupons:', error);
    }
  };

  const loadPromotions = async () => {
    try {
      const response = await axios.get(`${API}/admin/promotions`);
      setPromotions(response.data);
    } catch (error) {
      console.error('Error loading promotions:', error);
    }
  };

  const handleMakeAdmin = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/admin/users/make-admin`, newAdmin);
      alert('Admin criado com sucesso!');
      setNewAdmin({ email: '', name: '' });
      loadUsers();
    } catch (error) {
      alert(error.response?.data?.detail || 'Erro ao criar admin');
    }
  };

  const handleRemoveAdmin = async (userId) => {
    if (window.confirm('Tem certeza que quer remover este admin?')) {
      try {
        await axios.delete(`${API}/admin/users/${userId}/remove-admin`);
        alert('Admin removido!');
        loadUsers();
      } catch (error) {
        alert(error.response?.data?.detail || 'Erro ao remover admin');
      }
    }
  };

  // New functions for user management
  const handleChangePassword = (userItem) => {
    setPasswordModalUser(userItem);
    setShowPasswordModal(true);
    setNewPassword('');
  };

  const handleSavePassword = async () => {
    if (!newPassword || newPassword.length < 6) {
      alert('A senha deve ter pelo menos 6 caracteres');
      return;
    }
    
    try {
      await axios.put(`${API}/admin/users/${passwordModalUser.id}/password`, {
        new_password: newPassword
      });
      alert('Senha alterada com sucesso!');
      setShowPasswordModal(false);
      setPasswordModalUser(null);
      setNewPassword('');
    } catch (error) {
      alert(error.response?.data?.detail || 'Erro ao alterar senha');
    }
  };

  const handleDeleteUser = async (userId, userName) => {
    if (window.confirm(`Tem certeza que quer deletar o usuário ${userName}? Esta ação não pode ser desfeita.`)) {
      try {
        await axios.delete(`${API}/admin/users/${userId}`);
        alert('Usuário deletado com sucesso!');
        loadUsers();
      } catch (error) {
        alert(error.response?.data?.detail || 'Erro ao deletar usuário');
      }
    }
  };

  const handleUserSelection = (userId) => {
    setSelectedUsers(prev => 
      prev.includes(userId) 
        ? prev.filter(id => id !== userId)
        : [...prev, userId]
    );
  };

  const handleBulkMakeAdmin = async () => {
    if (selectedUsers.length === 0) {
      alert('Selecione pelo menos um usuário');
      return;
    }
    
    if (window.confirm(`Tem certeza que quer tornar ${selectedUsers.length} usuário(s) administrador(es)?`)) {
      try {
        await axios.post(`${API}/admin/users/bulk-make-admin`, {
          user_ids: selectedUsers
        });
        alert('Usuários promovidos a admin com sucesso!');
        setSelectedUsers([]);
        loadUsers();
      } catch (error) {
        alert(error.response?.data?.detail || 'Erro ao promover usuários');
      }
    }
  };

  if (!user?.is_admin) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black flex items-center justify-center">
        <div className="text-center text-white">
          <div className="text-8xl mb-4">🚫</div>
          <h1 className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold mb-4`}>Acesso Negado</h1>
          <p className={`${isMobile ? 'text-lg' : 'text-xl'} text-gray-400`}>Apenas administradores podem aceder a esta área.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <h1 className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold mb-12 text-center text-white`}>
          ⚙️ Painel de Administração
        </h1>

        {/* Dashboard Stats */}
        {dashboardData && (
          <div className={`grid ${isMobile ? 'grid-cols-1 gap-4' : 'md:grid-cols-4 gap-6'} mb-12`}>
            <div className="bg-gray-800/50 rounded-2xl p-6 border border-purple-500/30">
              <h3 className="text-purple-400 text-lg font-semibold mb-2">📦 Total Pedidos</h3>
              <p className="text-3xl font-bold text-white">{dashboardData.total_orders}</p>
            </div>
            <div className="bg-gray-800/50 rounded-2xl p-6 border border-purple-500/30">
              <h3 className="text-purple-400 text-lg font-semibold mb-2">👥 Utilizadores</h3>
              <p className="text-3xl font-bold text-white">{dashboardData.total_users}</p>
            </div>
            <div className="bg-gray-800/50 rounded-2xl p-6 border border-purple-500/30">
              <h3 className="text-purple-400 text-lg font-semibold mb-2">🎁 Produtos</h3>
              <p className="text-3xl font-bold text-white">{dashboardData.total_products}</p>
            </div>
            <div className="bg-gray-800/50 rounded-2xl p-6 border border-purple-500/30">
              <h3 className="text-purple-400 text-lg font-semibold mb-2">💰 Receita</h3>
              <p className="text-3xl font-bold text-white">€{dashboardData.total_revenue?.toFixed(2) || '0.00'}</p>
            </div>
          </div>
        )}

        {/* User Management Section */}
        {user?.email === 'eduardocorreia3344@gmail.com' && (
          <div className="bg-gray-800/50 rounded-2xl p-6 border border-purple-500/30 mb-8">
            <h2 className={`${isMobile ? 'text-xl' : 'text-2xl'} font-bold mb-6 text-white`}>👥 Gestão de Utilizadores</h2>
            
            {/* Create Admin Form */}
            <form onSubmit={handleMakeAdmin} className="mb-6">
              <div className={`${isMobile ? 'space-y-4' : 'flex gap-4 items-end'}`}>
                <input
                  type="email"
                  placeholder="Email do novo admin"
                  value={newAdmin.email}
                  onChange={(e) => setNewAdmin({...newAdmin, email: e.target.value})}
                  required
                  className="bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none flex-1"
                />
                <input
                  type="text"
                  placeholder="Nome do novo admin"
                  value={newAdmin.name}
                  onChange={(e) => setNewAdmin({...newAdmin, name: e.target.value})}
                  required
                  className="bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none flex-1"
                />
                <button
                  type="submit"
                  className="bg-gradient-to-r from-green-600 to-green-700 text-white px-6 py-3 rounded-lg hover:from-green-700 hover:to-green-800 transition-all duration-300"
                >
                  ➕ Adicionar Admin
                </button>
              </div>
            </form>

            {/* Bulk actions for selecting multiple users */}
            {selectedUsers.length > 0 && (
              <div className="mb-4 p-4 bg-purple-900/20 rounded-lg border border-purple-500/30">
                <p className="text-white mb-3">{selectedUsers.length} usuário(s) selecionado(s)</p>
                <button
                  onClick={handleBulkMakeAdmin}
                  className="bg-gradient-to-r from-purple-600 to-purple-700 text-white px-4 py-2 rounded-lg hover:from-purple-700 hover:to-purple-800 transition-all duration-300"
                >
                  ⚙️ Tornar Admins Selecionados
                </button>
              </div>
            )}

            {/* Users list */}
            <div className="overflow-x-auto">
              <table className="w-full text-white">
                <thead>
                  <tr className="border-b border-purple-500/30">
                    <th className="text-left py-3">Selecionar</th>
                    <th className="text-left py-3">Nome</th>
                    <th className="text-left py-3">Email</th>
                    <th className="text-left py-3">Tipo</th>
                    <th className="text-left py-3">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map(userItem => (
                    <tr key={userItem.id} className="border-b border-gray-700/50">
                      <td className="py-3">
                        {userItem.email !== 'eduardocorreia3344@gmail.com' && (
                          <input
                            type="checkbox"
                            checked={selectedUsers.includes(userItem.id)}
                            onChange={() => handleUserSelection(userItem.id)}
                            className="w-4 h-4 text-purple-600 bg-gray-700 border-gray-600 rounded focus:ring-purple-500"
                          />
                        )}
                      </td>
                      <td className="py-3">{userItem.name}</td>
                      <td className="py-3">{userItem.email}</td>
                      <td className="py-3">
                        {userItem.email === 'eduardocorreia3344@gmail.com' ? (
                          <span className="text-yellow-400">👑 Super Admin</span>
                        ) : userItem.is_admin ? (
                          <span className="text-purple-400">⚙️ Admin</span>
                        ) : (
                          <span className="text-gray-400">👤 Utilizador</span>
                        )}
                      </td>
                      <td className="py-3">
                        <div className="flex gap-2 flex-wrap">
                          {/* Change Password Button */}
                          {userItem.email !== 'eduardocorreia3344@gmail.com' && (
                            <button
                              onClick={() => handleChangePassword(userItem)}
                              className="text-blue-400 hover:text-blue-300 text-sm px-2 py-1 bg-blue-900/20 rounded"
                            >
                              🔑 Alterar Senha
                            </button>
                          )}
                          
                          {/* Remove Admin Button */}
                          {userItem.is_admin && userItem.email !== 'eduardocorreia3344@gmail.com' && (
                            <button
                              onClick={() => handleRemoveAdmin(userItem.id)}
                              className="text-orange-400 hover:text-orange-300 text-sm px-2 py-1 bg-orange-900/20 rounded"
                            >
                              🗑️ Remover Admin
                            </button>
                          )}
                          
                          {/* Delete User Button */}
                          {userItem.email !== 'eduardocorreia3344@gmail.com' && (
                            <button
                              onClick={() => handleDeleteUser(userItem.id, userItem.name)}
                              className="text-red-400 hover:text-red-300 text-sm px-2 py-1 bg-red-900/20 rounded"
                            >
                              ⚠️ Deletar Usuário
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className={`grid ${isMobile ? 'grid-cols-2 gap-4' : 'md:grid-cols-3 gap-6'}`}>
          <Link
            to="/admin/users"
            className="bg-gray-800/50 rounded-2xl p-8 border border-purple-500/30 hover:border-purple-400 transition-colors duration-300 text-center text-white"
          >
            <div className="text-5xl mb-4">👥</div>
            <h3 className={`${isMobile ? 'text-sm' : 'text-xl'} font-semibold`}>Gerir Utilizadores</h3>
          </Link>
          <Link
            to="/admin/orders"
            className="bg-gray-800/50 rounded-2xl p-8 border border-purple-500/30 hover:border-purple-400 transition-colors duration-300 text-center text-white"
          >
            <div className="text-5xl mb-4">📋</div>
            <h3 className={`${isMobile ? 'text-sm' : 'text-xl'} font-semibold`}>Gerir Pedidos</h3>
          </Link>
          <Link
            to="/admin/products"
            className="bg-gray-800/50 rounded-2xl p-8 border border-purple-500/30 hover:border-purple-400 transition-colors duration-300 text-center text-white"
          >
            <div className="text-5xl mb-4">🎁</div>
            <h3 className={`${isMobile ? 'text-sm' : 'text-xl'} font-semibold`}>Gerir Produtos</h3>
          </Link>
          <Link
            to="/admin/coupons"
            className="bg-gray-800/50 rounded-2xl p-8 border border-purple-500/30 hover:border-purple-400 transition-colors duration-300 text-center text-white"
          >
            <div className="text-5xl mb-4">🎫</div>
            <h3 className={`${isMobile ? 'text-sm' : 'text-xl'} font-semibold`}>Gerir Cupões</h3>
          </Link>
          <Link
            to="/admin/promotions"
            className="bg-gray-800/50 rounded-2xl p-8 border border-purple-500/30 hover:border-purple-400 transition-colors duration-300 text-center text-white"
          >
            <div className="text-5xl mb-4">🏷️</div>
            <h3 className={`${isMobile ? 'text-sm' : 'text-xl'} font-semibold`}>Promoções</h3>
          </Link>
          <Link
            to="/admin/categories"
            className="bg-gray-800/50 rounded-2xl p-8 border border-purple-500/30 hover:border-purple-400 transition-colors duration-300 text-center text-white"
          >
            <div className="text-5xl mb-4">🏷️</div>
            <h3 className={`${isMobile ? 'text-sm' : 'text-xl'} font-semibold`}>Gerir Categorias</h3>
          </Link>
          <Link
            to="/admin/emails"
            className="bg-gray-800/50 rounded-2xl p-8 border border-purple-500/30 hover:border-purple-400 transition-colors duration-300 text-center text-white"
          >
            <div className="text-5xl mb-4">📧</div>
            <h3 className={`${isMobile ? 'text-sm' : 'text-xl'} font-semibold`}>Emails</h3>
          </Link>
          <Link
            to="/admin/chat"
            className="bg-gray-800/50 rounded-2xl p-8 border border-purple-500/30 hover:border-purple-400 transition-colors duration-300 text-center text-white relative"
          >
            <div className="text-5xl mb-4">💬</div>
            <h3 className={`${isMobile ? 'text-sm' : 'text-xl'} font-semibold`}>Live Chat</h3>
            {pendingChatsCount > 0 && (
              <span className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold animate-pulse">
                {pendingChatsCount}
              </span>
            )}
          </Link>
          <Link
            to="/admin/subscriptions"
            className="bg-gray-800/50 rounded-2xl p-8 border border-purple-500/30 hover:border-purple-400 transition-colors duration-300 text-center text-white"
          >
            <div className="text-5xl mb-4">🔄</div>
            <h3 className={`${isMobile ? 'text-sm' : 'text-xl'} font-semibold`}>Assinaturas</h3>
          </Link>
        </div>
      </div>

      {/* Password Change Modal */}
      {showPasswordModal && passwordModalUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-2xl border border-purple-500/30 max-w-md w-full mx-4">
            <h3 className="text-xl font-bold text-white mb-4">
              Alterar Senha de {passwordModalUser.name}
            </h3>
            <div className="mb-4">
              <label className="block text-gray-300 mb-2">Nova Senha:</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Digite a nova senha (mín. 6 caracteres)"
                className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleSavePassword}
                className="flex-1 bg-gradient-to-r from-green-600 to-green-700 text-white px-4 py-2 rounded-lg hover:from-green-700 hover:to-green-800 transition-all duration-300"
              >
                💾 Salvar Nova Senha
              </button>
              <button
                onClick={() => {
                  setShowPasswordModal(false);
                  setPasswordModalUser(null);
                  setNewPassword('');
                }}
                className="flex-1 bg-gradient-to-r from-gray-600 to-gray-700 text-white px-4 py-2 rounded-lg hover:from-gray-700 hover:to-gray-800 transition-all duration-300"
              >
                ❌ Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Admin sub-pages
const AdminOrders = () => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [showOrderDetails, setShowOrderDetails] = useState(false);
  const { user } = useDeviceContext();
  const isMobile = useIsMobile();

  useEffect(() => {
    if (user?.is_admin) {
      loadOrders();
    }
  }, [user]);

  const loadOrders = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/admin/orders`);
      setOrders(response.data);
    } catch (error) {
      console.error('Error loading orders:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateOrderStatus = async (orderId, newStatus) => {
    try {
      await axios.put(`${API}/admin/orders/${orderId}/status`, null, {
        params: { status: newStatus }
      });
      alert('Status atualizado com sucesso!');
      loadOrders();
    } catch (error) {
      console.error('Error updating order status:', error);
      alert('Erro ao atualizar status: ' + (error.response?.data?.detail || 'Erro desconhecido'));
    }
  };

  const handleViewOrderDetails = async (orderId) => {
    try {
      const response = await axios.get(`${API}/admin/orders/${orderId}`);
      setSelectedOrder(response.data);
      setShowOrderDetails(true);
    } catch (error) {
      console.error('Error loading order details:', error);
      alert('Erro ao carregar detalhes do pedido');
    }
  };

  if (!user?.is_admin) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black flex items-center justify-center">
        <div className="text-center text-white">
          <div className="text-8xl mb-4">🚫</div>
          <h1 className="text-4xl font-bold mb-4">Acesso Negado</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <div className="flex items-center mb-8">
          <Link to="/admin" className="text-purple-400 hover:text-purple-300 mr-4">
            ← Voltar ao Admin
          </Link>
          <h1 className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold text-white`}>
            📋 Gestão de Pedidos
          </h1>
        </div>

        {loading ? (
          <div className="text-center text-white">
            <div className="animate-spin text-6xl mb-4">🔮</div>
            <p>Carregando pedidos...</p>
          </div>
        ) : (
          <div className="bg-gray-800/50 rounded-2xl border border-purple-500/30 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-white">
                <thead className="bg-purple-900/50">
                  <tr>
                    <th className="text-left p-4">ID do Pedido</th>
                    <th className="text-left p-4">Cliente</th>
                    <th className="text-left p-4">Total</th>
                    <th className="text-left p-4">Status Pagamento</th>
                    <th className="text-left p-4">Status Pedido</th>
                    <th className="text-left p-4">Data</th>
                    <th className="text-left p-4">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((order) => (
                    <tr key={order.id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                      <td className="p-4 font-mono text-sm">#{order.id.slice(0, 8)}</td>
                      <td className="p-4">{order.user_id || 'Convidado'}</td>
                      <td className="p-4 font-bold text-green-400">€{order.total_amount?.toFixed(2)}</td>
                      <td className="p-4">
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          order.payment_status === 'paid' ? 'bg-green-900 text-green-300' : 
                          order.payment_status === 'pending' ? 'bg-yellow-900 text-yellow-300' :
                          'bg-red-900 text-red-300'
                        }`}>
                          {order.payment_status}
                        </span>
                      </td>
                      <td className="p-4">
                        <select
                          value={order.order_status}
                          onChange={(e) => handleUpdateOrderStatus(order.id, e.target.value)}
                          className="bg-gray-700 text-white border border-purple-500/30 rounded px-2 py-1 text-sm"
                        >
                          <option value="pending">Pendente</option>
                          <option value="confirmed">Confirmado</option>
                          <option value="processing">Processando</option>
                          <option value="shipped">Enviado</option>
                          <option value="delivered">Entregue</option>
                          <option value="cancelled">Cancelado</option>
                        </select>
                      </td>
                      <td className="p-4 text-sm text-gray-400">
                        {new Date(order.created_at).toLocaleDateString('pt-PT')}
                      </td>
                      <td className="p-4">
                        <button 
                          onClick={() => handleViewOrderDetails(order.id)}
                          className="text-purple-400 hover:text-purple-300 text-sm"
                        >
                          📋 Ver Detalhes
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {orders.length === 0 && (
              <div className="text-center py-12 text-gray-400">
                <div className="text-6xl mb-4">📦</div>
                <p>Nenhum pedido encontrado</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Admin Users Management Component
const AdminUsers = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [passwordModalUser, setPasswordModalUser] = useState(null);
  const [newPassword, setNewPassword] = useState('');
  const { user } = useDeviceContext();
  const isMobile = useIsMobile();

  useEffect(() => {
    if (user?.is_admin) {
      loadUsers();
    }
  }, [user, searchTerm]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const params = searchTerm ? { search: searchTerm } : {};
      const response = await axios.get(`${API}/admin/users`, { params });
      setUsers(response.data);
    } catch (error) {
      console.error('Error loading users:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectUser = (userId) => {
    setSelectedUsers(prev => 
      prev.includes(userId) 
        ? prev.filter(id => id !== userId)
        : [...prev, userId]
    );
  };

  const handleSelectAll = () => {
    if (selectedUsers.length === users.length) {
      setSelectedUsers([]);
    } else {
      setSelectedUsers(users.map(u => u.id));
    }
  };

  const handleBulkDelete = async () => {
    if (selectedUsers.length === 0) {
      alert('Selecione pelo menos um usuário');
      return;
    }

    if (!window.confirm(`Tem certeza que quer deletar ${selectedUsers.length} usuários? Esta ação não pode ser desfeita.`)) {
      return;
    }

    try {
      const response = await axios.post(`${API}/admin/users/bulk-delete`, {
        user_ids: selectedUsers
      });
      alert(response.data.message);
      setSelectedUsers([]);
      loadUsers();
    } catch (error) {
      alert(error.response?.data?.detail || 'Erro ao deletar usuários');
    }
  };

  const handleChangePassword = (userItem) => {
    setPasswordModalUser(userItem);
    setShowPasswordModal(true);
    setNewPassword('');
  };

  const handleSavePassword = async () => {
    if (!newPassword || newPassword.length < 6) {
      alert('A senha deve ter pelo menos 6 caracteres');
      return;
    }
    
    try {
      await axios.put(`${API}/admin/users/${passwordModalUser.id}/password`, {
        new_password: newPassword
      });
      alert('Senha alterada com sucesso!');
      setShowPasswordModal(false);
      setPasswordModalUser(null);
      setNewPassword('');
    } catch (error) {
      alert(error.response?.data?.detail || 'Erro ao alterar senha');
    }
  };

  const handleDeleteUser = async (userId, userName) => {
    if (!window.confirm(`Tem certeza que quer deletar o usuário ${userName}? Esta ação não pode ser desfeita.`)) {
      return;
    }

    try {
      await axios.delete(`${API}/admin/users/${userId}`);
      alert('Usuário deletado com sucesso!');
      loadUsers();
    } catch (error) {
      alert(error.response?.data?.detail || 'Erro ao deletar usuário');
    }
  };

  if (!user?.is_admin) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black flex items-center justify-center">
        <div className="text-center text-white">
          <div className="text-8xl mb-4">🚫</div>
          <h1 className="text-4xl font-bold mb-4">Acesso Negado</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <div className="flex items-center mb-8">
          <Link to="/admin" className="text-purple-400 hover:text-purple-300 mr-4">
            ← Voltar ao Admin
          </Link>
          <h1 className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold text-white`}>
            👥 Gestão de Utilizadores
          </h1>
        </div>

        {/* Search and Actions */}
        <div className="bg-gray-800/50 rounded-2xl p-6 mb-8 border border-purple-500/30">
          <div className={`${isMobile ? 'space-y-4' : 'flex items-center justify-between'}`}>
            <div className={`${isMobile ? 'w-full' : 'flex-1 max-w-md'}`}>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Pesquisar por nome ou email..."
                className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
              />
            </div>
            <div className={`${isMobile ? 'flex flex-col space-y-2' : 'flex space-x-4'}`}>
              <button
                onClick={handleBulkDelete}
                disabled={selectedUsers.length === 0}
                className={`${isMobile ? 'w-full' : ''} bg-red-600 hover:bg-red-700 disabled:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors duration-300 disabled:cursor-not-allowed`}
              >
                🗑️ Deletar Selecionados ({selectedUsers.length})
              </button>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="text-center text-white">
            <div className="animate-spin text-6xl mb-4">🔮</div>
            <p>Carregando utilizadores...</p>
          </div>
        ) : (
          <div className="bg-gray-800/50 rounded-2xl border border-purple-500/30 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-white">
                <thead className="bg-purple-900/50">
                  <tr>
                    <th className="text-left p-4">
                      <input
                        type="checkbox"
                        checked={selectedUsers.length === users.length}
                        onChange={handleSelectAll}
                        className="scale-125"
                      />
                    </th>
                    <th className="text-left p-4">Nome</th>
                    <th className="text-left p-4">Email</th>
                    <th className="text-left p-4">Telefone</th>
                    <th className="text-left p-4">Cidade</th>
                    <th className="text-left p-4">Admin</th>
                    <th className="text-left p-4">Data Registo</th>
                    <th className="text-left p-4">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((userItem) => (
                    <tr key={userItem.id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                      <td className="p-4">
                        <input
                          type="checkbox"
                          checked={selectedUsers.includes(userItem.id)}
                          onChange={() => handleSelectUser(userItem.id)}
                          className="scale-125"
                        />
                      </td>
                      <td className="p-4 font-semibold">{userItem.name}</td>
                      <td className="p-4">{userItem.email}</td>
                      <td className="p-4 text-gray-400">{userItem.phone || 'N/A'}</td>
                      <td className="p-4 text-gray-400">{userItem.city || 'N/A'}</td>
                      <td className="p-4">
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          userItem.is_super_admin ? 'bg-red-900 text-red-300' :
                          userItem.is_admin ? 'bg-blue-900 text-blue-300' : 
                          'bg-gray-900 text-gray-300'
                        }`}>
                          {userItem.is_super_admin ? 'Super Admin' :
                           userItem.is_admin ? 'Admin' : 'Utilizador'}
                        </span>
                      </td>
                      <td className="p-4 text-sm text-gray-400">
                        {new Date(userItem.created_at).toLocaleDateString('pt-PT')}
                      </td>
                      <td className="p-4">
                        <div className="flex space-x-2">
                          <button
                            onClick={() => handleChangePassword(userItem)}
                            className="text-blue-400 hover:text-blue-300 text-sm"
                            title="Alterar senha"
                          >
                            🔑
                          </button>
                          {!userItem.is_super_admin && userItem.email !== user.email && (
                            <button
                              onClick={() => handleDeleteUser(userItem.id, userItem.name)}
                              className="text-red-400 hover:text-red-300 text-sm"
                              title="Deletar usuário"
                            >
                              🗑️
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {users.length === 0 && (
              <div className="text-center py-12 text-gray-400">
                <div className="text-6xl mb-4">👥</div>
                <p>Nenhum utilizador encontrado</p>
              </div>
            )}
          </div>
        )}

        {/* Password Change Modal */}
        {showPasswordModal && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
            <div className="bg-gray-800 rounded-2xl p-8 border border-purple-500/30 max-w-md w-full mx-4">
              <h3 className="text-2xl font-bold text-white mb-6">
                🔑 Alterar Senha
              </h3>
              <p className="text-gray-300 mb-4">
                Usuário: <strong>{passwordModalUser?.name}</strong>
              </p>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Nova senha (mín. 6 caracteres)"
                className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 mb-6 focus:border-purple-400 focus:outline-none"
              />
              <div className="flex space-x-4">
                <button
                  onClick={handleSavePassword}
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white py-3 rounded-lg transition-colors duration-300"
                >
                  ✅ Salvar
                </button>
                <button
                  onClick={() => setShowPasswordModal(false)}
                  className="flex-1 bg-gray-600 hover:bg-gray-700 text-white py-3 rounded-lg transition-colors duration-300"
                >
                  ❌ Cancelar
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const AdminProducts = () => {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    category: '',
    price: '',
    image_url: '',
    image_base64: '', // Para armazenar a imagem principal em base64
    images: [], // URLs de imagens adicionais
    images_base64: [], // Imagens adicionais em base64
    stock_quantity: '100',
    featured: false,
    subscription_prices: {
      "3_months": '',
      "6_months": '',
      "12_months": ''
    }
  });
  const { user } = useDeviceContext();
  const isMobile = useIsMobile();

  useEffect(() => {
    if (user?.is_admin) {
      loadProducts();
      loadCategories();
    }
  }, [user]);

  const loadProducts = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/products`);
      setProducts(response.data);
    } catch (error) {
      console.error('Error loading products:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async () => {
    try {
      const response = await axios.get(`${API}/categories`);
      setCategories(response.data);
    } catch (error) {
      console.error('Error loading categories:', error);
    }
  };

  // Função para converter imagem principal para base64
  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) { // 5MB limit
        alert('A imagem deve ter menos de 5MB');
        return;
      }
      
      const reader = new FileReader();
      reader.onload = (event) => {
        const base64String = event.target.result;
        setFormData({
          ...formData,
          image_base64: base64String,
          image_url: '' // Clear URL if uploading file
        });
      };
      reader.readAsDataURL(file);
    }
  };

  // Função para converter múltiplas imagens para base64
  const handleMultipleImageUpload = (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    // Check each file size
    for (let file of files) {
      if (file.size > 5 * 1024 * 1024) {
        alert('Cada imagem deve ter menos de 5MB');
        return;
      }
    }

    // Convert all files to base64
    const promises = files.map(file => {
      return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = (event) => resolve(event.target.result);
        reader.readAsDataURL(file);
      });
    });

    Promise.all(promises).then(base64Images => {
      setFormData({
        ...formData,
        images_base64: [...formData.images_base64, ...base64Images]
      });
    });
  };

  // Função para remover imagem adicional
  const removeAdditionalImage = (index, isBase64 = false) => {
    if (isBase64) {
      setFormData({
        ...formData,
        images_base64: formData.images_base64.filter((_, i) => i !== index)
      });
    } else {
      setFormData({
        ...formData,
        images: formData.images.filter((_, i) => i !== index)
      });
    }
  };

  // Função para adicionar URL de imagem adicional
  const addImageUrl = () => {
    const url = prompt('Digite a URL da imagem:');
    if (url && url.trim()) {
      setFormData({
        ...formData,
        images: [...formData.images, url.trim()]
      });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      // Prepare the product data according to the backend ProductCreate model
      const productData = {
        name: formData.name,
        description: formData.description,
        category: formData.category,
        price: parseFloat(formData.price),
        stock_quantity: parseInt(formData.stock_quantity),
        featured: formData.featured,
        subscription_prices: {
          "3_months": parseFloat(formData.subscription_prices["3_months"]) || 0,
          "6_months": parseFloat(formData.subscription_prices["6_months"]) || 0,
          "12_months": parseFloat(formData.subscription_prices["12_months"]) || 0
        },
        // Primary image handling (backwards compatibility)
        image_url: formData.image_base64 || formData.image_url || "",
        image_base64: formData.image_base64 || null,
        // Multiple images handling 
        images: formData.images || [],
        images_base64: formData.images_base64 || []
      };

      // Log the data being sent for debugging
      console.log('Sending product data:', productData);

      if (editingProduct) {
        const response = await axios.put(`${API}/admin/products/${editingProduct.id}`, productData);
        console.log('Update response:', response.data);
        alert('Produto atualizado com sucesso!');
      } else {
        const response = await axios.post(`${API}/admin/products`, productData);
        console.log('Create response:', response.data);
        alert('Produto criado com sucesso!');
      }

      // Reset form after successful submission
      setFormData({
        name: '',
        description: '',
        category: '',
        price: '',
        image_url: '',
        image_base64: '',
        images: [],
        images_base64: [],
        stock_quantity: '100',
        featured: false,
        subscription_prices: {
          "3_months": '',
          "6_months": '',
          "12_months": ''
        }
      });
      setShowAddForm(false);
      setEditingProduct(null);
      loadProducts();
    } catch (error) {
      console.error('Error saving product:', error);
      console.error('Error response:', error.response?.data);
      alert(`Erro ao salvar produto: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleEdit = (product) => {
    setEditingProduct(product);
    setFormData({
      name: product.name,
      description: product.description,
      category: product.category,
      price: product.price.toString(),
      image_url: product.image_url,
      image_base64: '',
      images: product.images || [], // Load existing images
      images_base64: [], // Reset base64 images (will be populated if user uploads new ones)
      stock_quantity: product.stock_quantity.toString(),
      featured: product.featured,
      subscription_prices: {
        "3_months": product.subscription_prices?.["3_months"]?.toString() || '',
        "6_months": product.subscription_prices?.["6_months"]?.toString() || '',
        "12_months": product.subscription_prices?.["12_months"]?.toString() || ''
      }
    });
    setShowAddForm(true);
  };

  const handleDelete = async (productId) => {
    if (window.confirm('Tem certeza que quer remover este produto?')) {
      try {
        await axios.delete(`${API}/admin/products/${productId}`);
        alert('Produto removido!');
        loadProducts();
      } catch (error) {
        alert('Erro ao remover produto');
      }
    }
  };

  if (!user?.is_admin) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black flex items-center justify-center">
        <div className="text-center text-white">
          <div className="text-8xl mb-4">🚫</div>
          <h1 className="text-4xl font-bold mb-4">Acesso Negado</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center">
            <Link to="/admin" className="text-purple-400 hover:text-purple-300 mr-4">
              ← Voltar ao Admin
            </Link>
            <h1 className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold text-white`}>
              🎁 Gestão de Produtos
            </h1>
          </div>
          <button
            onClick={() => {
              setShowAddForm(!showAddForm);
              setEditingProduct(null);
              setFormData({
                name: '',
                description: '',
                category: '',
                price: '',
                image_url: '',
                image_base64: '',
                images: [],
                images_base64: [],
                stock_quantity: '100',
                featured: false,
                subscription_prices: {
                  "3_months": '',
                  "6_months": '',
                  "12_months": ''
                }
              });
            }}
            className="bg-gradient-to-r from-green-600 to-green-700 text-white px-6 py-3 rounded-lg hover:from-green-700 hover:to-green-800 transition-all duration-300"
          >
            ➕ Novo Produto
          </button>
        </div>

        {showAddForm && (
          <div className="bg-gray-800/50 rounded-2xl p-8 mb-8 border border-purple-500/30">
            <h3 className="text-2xl font-bold mb-6 text-white">
              {editingProduct ? '✏️ Editar Produto' : '➕ Novo Produto'}
            </h3>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Nome do Produto</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                    placeholder="Mystery Box Geek..."
                  />
                </div>
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Categoria</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({...formData, category: e.target.value})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                  >
                    <option value="">Selecionar categoria</option>
                    {categories.map(cat => (
                      <option key={cat.id} value={cat.id}>{cat.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-lg font-medium mb-3 text-gray-300">Descrição</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  required
                  rows="4"
                  className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                  placeholder="Descrição detalhada do produto..."
                />
              </div>

              <div className="grid md:grid-cols-3 gap-6">
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Preço (€)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.price}
                    onChange={(e) => setFormData({...formData, price: e.target.value})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                    placeholder="29.99"
                  />
                </div>
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Stock</label>
                  <input
                    type="number"
                    value={formData.stock_quantity}
                    onChange={(e) => setFormData({...formData, stock_quantity: e.target.value})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                    placeholder="100"
                  />
                </div>
                <div className="flex items-center">
                  <label className="flex items-center text-gray-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.featured}
                      onChange={(e) => setFormData({...formData, featured: e.target.checked})}
                      className="mr-3 scale-125"
                    />
                    ⭐ Produto em Destaque
                  </label>
                </div>
              </div>

              {/* Subscription Prices Section */}
              <div className="bg-gray-700/30 rounded-lg p-6 border border-purple-500/20">
                <h4 className="text-lg font-semibold mb-4 text-white">📅 Preços de Assinatura (Opcional)</h4>
                <div className="grid md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2 text-gray-300">3 Meses (€)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.subscription_prices["3_months"]}
                      onChange={(e) => setFormData({
                        ...formData, 
                        subscription_prices: {
                          ...formData.subscription_prices,
                          "3_months": e.target.value
                        }
                      })}
                      className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                      placeholder="22.99"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2 text-gray-300">6 Meses (€)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.subscription_prices["6_months"]}
                      onChange={(e) => setFormData({
                        ...formData, 
                        subscription_prices: {
                          ...formData.subscription_prices,
                          "6_months": e.target.value
                        }
                      })}
                      className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                      placeholder="19.99"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2 text-gray-300">12 Meses (€)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.subscription_prices["12_months"]}
                      onChange={(e) => setFormData({
                        ...formData, 
                        subscription_prices: {
                          ...formData.subscription_prices,
                          "12_months": e.target.value
                        }
                      })}
                      className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                      placeholder="16.99"
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <label className="block text-lg font-medium mb-3 text-gray-300">Imagem do Produto</label>
                
                {/* Preview da imagem atual */}
                {(formData.image_base64 || formData.image_url) && (
                  <div className="mb-4">
                    <img 
                      src={formData.image_base64 || formData.image_url} 
                      alt="Preview" 
                      className="w-32 h-32 object-cover rounded-lg border border-purple-500/30"
                    />
                  </div>
                )}
                
                {/* Upload de arquivo */}
                <div>
                  <label className="block text-sm font-medium mb-2 text-gray-400">Enviar Imagem (Max: 5MB)</label>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageUpload}
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-purple-600 file:text-white hover:file:bg-purple-700"
                  />
                </div>
                
                <div className="text-center text-gray-400">OU</div>
                
                {/* URL da imagem */}
                <div>
                  <label className="block text-sm font-medium mb-2 text-gray-400">URL da Imagem</label>
                  <input
                    type="url"
                    value={formData.image_url}
                    onChange={(e) => setFormData({...formData, image_url: e.target.value, image_base64: ''})}
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                    placeholder="https://exemplo.com/imagem.jpg"
                  />
                </div>
              </div>

              {/* Multiple Images Section */}
              <div className="bg-gray-700/30 rounded-lg p-6 border border-purple-500/20">
                <h4 className="text-lg font-semibold mb-4 text-white">🖼️ Galeria de Imagens (Opcional)</h4>
                
                {/* Upload múltiplas imagens */}
                <div className="mb-4">
                  <label className="block text-sm font-medium mb-2 text-gray-400">Adicionar Múltiplas Imagens (Max: 5MB cada)</label>
                  <input
                    type="file"
                    accept="image/*"
                    multiple
                    onChange={handleMultipleImageUpload}
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-green-600 file:text-white hover:file:bg-green-700"
                  />
                </div>

                {/* Botão para adicionar URL */}
                <div className="mb-4">
                  <button
                    type="button"
                    onClick={addImageUrl}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors duration-300 text-sm"
                  >
                    🔗 Adicionar URL de Imagem
                  </button>
                </div>

                {/* Preview das imagens adicionais */}
                {(formData.images_base64.length > 0 || formData.images.length > 0) && (
                  <div className="space-y-4">
                    <h5 className="text-sm font-medium text-gray-300">Imagens da Galeria:</h5>
                    
                    {/* Imagens Base64 */}
                    {formData.images_base64.length > 0 && (
                      <div>
                        <p className="text-xs text-gray-400 mb-2">Imagens enviadas:</p>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                          {formData.images_base64.map((image, index) => (
                            <div key={`base64-${index}`} className="relative group">
                              <img 
                                src={image} 
                                alt={`Galeria ${index + 1}`} 
                                className="w-full h-20 object-cover rounded-lg border border-purple-500/30"
                              />
                              <button
                                type="button"
                                onClick={() => removeAdditionalImage(index, true)}
                                className="absolute -top-2 -right-2 bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs hover:bg-red-700 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
                              >
                                ✕
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Imagens URL */}
                    {formData.images.length > 0 && (
                      <div>
                        <p className="text-xs text-gray-400 mb-2">Imagens por URL:</p>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                          {formData.images.map((imageUrl, index) => (
                            <div key={`url-${index}`} className="relative group">
                              <img 
                                src={imageUrl} 
                                alt={`URL ${index + 1}`} 
                                className="w-full h-20 object-cover rounded-lg border border-purple-500/30"
                                onError={(e) => {
                                  e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="%23374151"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="%239CA3AF">Erro</text></svg>';
                                }}
                              />
                              <button
                                type="button"
                                onClick={() => removeAdditionalImage(index, false)}
                                className="absolute -top-2 -right-2 bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs hover:bg-red-700 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
                              >
                                ✕
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="flex gap-4">
                <button
                  type="submit"
                  className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-8 py-3 rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all duration-300"
                >
                  {editingProduct ? '💾 Atualizar' : '➕ Criar'} Produto
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowAddForm(false);
                    setEditingProduct(null);
                  }}
                  className="bg-gray-600 text-white px-8 py-3 rounded-lg hover:bg-gray-700 transition-all duration-300"
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        )}

        {loading ? (
          <div className="text-center text-white">
            <div className="animate-spin text-6xl mb-4">🔮</div>
            <p>Carregando produtos...</p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {products.map((product) => (
              <div key={product.id} className="bg-gray-800/50 rounded-2xl border border-purple-500/30 overflow-hidden hover:border-purple-400 transition-colors duration-300">
                <img
                  src={product.image_url}
                  alt={product.name}
                  className="w-full h-48 object-cover"
                />
                <div className="p-6">
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="text-lg font-semibold text-white">{product.name}</h3>
                    {product.featured && (
                      <span className="bg-yellow-500 text-black px-2 py-1 rounded-full text-xs font-bold">
                        ⭐ Destaque
                      </span>
                    )}
                  </div>
                  <p className="text-gray-300 text-sm mb-4 line-clamp-3">{product.description}</p>
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-2xl font-bold text-purple-400">€{product.price}</span>
                    <span className="text-sm text-gray-400">Stock: {product.stock_quantity}</span>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleEdit(product)}
                      className="flex-1 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors duration-300 text-sm"
                    >
                      ✏️ Editar
                    </button>
                    <button
                      onClick={() => handleDelete(product.id)}
                      className="flex-1 bg-red-600 text-white py-2 rounded-lg hover:bg-red-700 transition-colors duration-300 text-sm"
                    >
                      🗑️ Remover
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {products.length === 0 && !loading && (
          <div className="text-center py-12 text-gray-400">
            <div className="text-6xl mb-4">🎁</div>
            <p>Nenhum produto encontrado</p>
          </div>
        )}
      </div>
    </div>
  );
};

const AdminCoupons = () => {
  const [coupons, setCoupons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingCoupon, setEditingCoupon] = useState(null);
  const [formData, setFormData] = useState({
    code: '',
    description: '',
    discount_type: 'percentage',
    discount_value: '',
    min_order_value: '',
    max_uses: '',
    valid_from: '',
    valid_until: ''
  });
  const { user } = useDeviceContext();
  const isMobile = useIsMobile();

  useEffect(() => {
    if (user?.is_admin) {
      loadCoupons();
    }
  }, [user]);

  const loadCoupons = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/admin/coupons`);
      setCoupons(response.data);
    } catch (error) {
      console.error('Error loading coupons:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const couponData = {
        ...formData,
        code: formData.code.toUpperCase(),
        discount_value: parseFloat(formData.discount_value),
        min_order_value: formData.min_order_value ? parseFloat(formData.min_order_value) : null,
        max_uses: formData.max_uses ? parseInt(formData.max_uses) : null,
        valid_from: new Date(formData.valid_from).toISOString(),
        valid_until: new Date(formData.valid_until).toISOString()
      };

      if (editingCoupon) {
        await axios.put(`${API}/admin/coupons/${editingCoupon.id}`, couponData);
        alert('Cupão atualizado com sucesso!');
      } else {
        await axios.post(`${API}/admin/coupons`, couponData);
        alert('Cupão criado com sucesso!');
      }

      setFormData({
        code: '',
        description: '',
        discount_type: 'percentage',
        discount_value: '',
        min_order_value: '',
        max_uses: '',
        valid_from: '',
        valid_until: ''
      });
      setShowAddForm(false);
      setEditingCoupon(null);
      loadCoupons();
    } catch (error) {
      alert(error.response?.data?.detail || 'Erro ao salvar cupão');
    }
  };

  const handleEdit = (coupon) => {
    setEditingCoupon(coupon);
    setFormData({
      code: coupon.code,
      description: coupon.description,
      discount_type: coupon.discount_type,
      discount_value: coupon.discount_value.toString(),
      min_order_value: coupon.min_order_value?.toString() || '',
      max_uses: coupon.max_uses?.toString() || '',
      valid_from: coupon.valid_from ? new Date(coupon.valid_from).toISOString().split('T')[0] : '',
      valid_until: coupon.valid_until ? new Date(coupon.valid_until).toISOString().split('T')[0] : ''
    });
    setShowAddForm(true);
  };

  const handleDelete = async (couponId) => {
    if (window.confirm('Tem certeza que quer desativar este cupão?')) {
      try {
        await axios.delete(`${API}/admin/coupons/${couponId}`);
        alert('Cupão desativado!');
        loadCoupons();
      } catch (error) {
        alert('Erro ao desativar cupão');
      }
    }
  };

  if (!user?.is_admin) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black flex items-center justify-center">
        <div className="text-center text-white">
          <div className="text-8xl mb-4">🚫</div>
          <h1 className="text-4xl font-bold mb-4">Acesso Negado</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center">
            <Link to="/admin" className="text-purple-400 hover:text-purple-300 mr-4">
              ← Voltar ao Admin
            </Link>
            <h1 className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold text-white`}>
              🎫 Gestão de Cupões
            </h1>
          </div>
          <button
            onClick={() => {
              setShowAddForm(!showAddForm);
              setEditingCoupon(null);
              setFormData({
                code: '',
                description: '',
                discount_type: 'percentage',
                discount_value: '',
                min_order_value: '',
                max_uses: '',
                valid_from: '',
                valid_until: ''
              });
            }}
            className="bg-gradient-to-r from-green-600 to-green-700 text-white px-6 py-3 rounded-lg hover:from-green-700 hover:to-green-800 transition-all duration-300"
          >
            ➕ Novo Cupão
          </button>
        </div>

        {showAddForm && (
          <div className="bg-gray-800/50 rounded-2xl p-8 mb-8 border border-purple-500/30">
            <h3 className="text-2xl font-bold mb-6 text-white">
              {editingCoupon ? '✏️ Editar Cupão' : '➕ Novo Cupão'}
            </h3>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Código do Cupão</label>
                  <input
                    type="text"
                    value={formData.code}
                    onChange={(e) => setFormData({...formData, code: e.target.value.toUpperCase()})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                    placeholder="DESCONTO10"
                  />
                </div>
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Tipo de Desconto</label>
                  <select
                    value={formData.discount_type}
                    onChange={(e) => setFormData({...formData, discount_type: e.target.value})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                  >
                    <option value="percentage">Percentagem (%)</option>
                    <option value="fixed">Valor Fixo (€)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-lg font-medium mb-3 text-gray-300">Descrição</label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  required
                  className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                  placeholder="Desconto de 10% em todos os produtos"
                />
              </div>

              <div className="grid md:grid-cols-3 gap-6">
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">
                    Valor do Desconto {formData.discount_type === 'percentage' ? '(%)' : '(€)'}
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.discount_value}
                    onChange={(e) => setFormData({...formData, discount_value: e.target.value})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                    placeholder={formData.discount_type === 'percentage' ? '10' : '5.00'}
                  />
                </div>
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Valor Mínimo (€)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.min_order_value}
                    onChange={(e) => setFormData({...formData, min_order_value: e.target.value})}
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                    placeholder="0.00"
                  />
                </div>
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Máximo de Usos</label>
                  <input
                    type="number"
                    value={formData.max_uses}
                    onChange={(e) => setFormData({...formData, max_uses: e.target.value})}
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                    placeholder="Ilimitado"
                  />
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Válido De</label>
                  <input
                    type="date"
                    value={formData.valid_from}
                    onChange={(e) => setFormData({...formData, valid_from: e.target.value})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Válido Até</label>
                  <input
                    type="date"
                    value={formData.valid_until}
                    onChange={(e) => setFormData({...formData, valid_until: e.target.value})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex gap-4">
                <button
                  type="submit"
                  className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-8 py-3 rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all duration-300"
                >
                  {editingCoupon ? '💾 Atualizar' : '➕ Criar'} Cupão
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowAddForm(false);
                    setEditingCoupon(null);
                  }}
                  className="bg-gray-600 text-white px-8 py-3 rounded-lg hover:bg-gray-700 transition-all duration-300"
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        )}

        {loading ? (
          <div className="text-center text-white">
            <div className="animate-spin text-6xl mb-4">🔮</div>
            <p>Carregando cupões...</p>
          </div>
        ) : (
          <div className="bg-gray-800/50 rounded-2xl border border-purple-500/30 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-white">
                <thead className="bg-purple-900/50">
                  <tr>
                    <th className="text-left p-4">Código</th>
                    <th className="text-left p-4">Descrição</th>
                    <th className="text-left p-4">Desconto</th>
                    <th className="text-left p-4">Usos</th>
                    <th className="text-left p-4">Validade</th>
                    <th className="text-left p-4">Status</th>
                    <th className="text-left p-4">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {coupons.map((coupon) => (
                    <tr key={coupon.id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                      <td className="p-4 font-mono font-bold text-purple-400">{coupon.code}</td>
                      <td className="p-4">{coupon.description}</td>
                      <td className="p-4 font-bold text-green-400">
                        {coupon.discount_type === 'percentage' 
                          ? `${coupon.discount_value}%` 
                          : `€${coupon.discount_value}`}
                      </td>
                      <td className="p-4">
                        {coupon.current_uses}/{coupon.max_uses || '∞'}
                      </td>
                      <td className="p-4 text-sm">
                        {new Date(coupon.valid_from).toLocaleDateString('pt-PT')} - {new Date(coupon.valid_until).toLocaleDateString('pt-PT')}
                      </td>
                      <td className="p-4">
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          coupon.is_active 
                            ? 'bg-green-900 text-green-300' 
                            : 'bg-red-900 text-red-300'
                        }`}>
                          {coupon.is_active ? 'Ativo' : 'Inativo'}
                        </span>
                      </td>
                      <td className="p-4">
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleEdit(coupon)}
                            className="text-blue-400 hover:text-blue-300 text-sm"
                          >
                            ✏️ Editar
                          </button>
                          <button
                            onClick={() => handleDelete(coupon.id)}
                            className="text-red-400 hover:text-red-300 text-sm"
                          >
                            🗑️ Desativar
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {coupons.length === 0 && (
              <div className="text-center py-12 text-gray-400">
                <div className="text-6xl mb-4">🎫</div>
                <p>Nenhum cupão encontrado</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const AdminCategories = () => {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    emoji: '',
    color: '#8B5CF6'
  });
  const { user } = useDeviceContext();
  const isMobile = useIsMobile();

  useEffect(() => {
    if (user?.is_admin) {
      loadCategories();
    }
  }, [user]);

  const loadCategories = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/categories`);
      setCategories(response.data);
    } catch (error) {
      console.error('Error loading categories:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCategory = async (categoryId, categoryName) => {
    if (window.confirm(`Tem a certeza que deseja remover a categoria "${categoryName}"? Esta ação não pode ser desfeita.`)) {
      try {
        await axios.delete(`${API}/admin/categories/${categoryId}`);
        alert('Categoria removida com sucesso!');
        loadCategories();
      } catch (error) {
        alert(error.response?.data?.detail || 'Erro ao remover categoria');
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/admin/categories`, formData);
      alert('Categoria criada com sucesso!');
      setFormData({
        name: '',
        description: '',
        emoji: '',
        color: '#8B5CF6'
      });
      setShowAddForm(false);
      loadCategories();
    } catch (error) {
      alert('Erro ao criar categoria');
    }
  };

  if (!user?.is_admin) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black flex items-center justify-center">
        <div className="text-center text-white">
          <div className="text-8xl mb-4">🚫</div>
          <h1 className="text-4xl font-bold mb-4">Acesso Negado</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center">
            <Link to="/admin" className="text-purple-400 hover:text-purple-300 mr-4">
              ← Voltar ao Admin
            </Link>
            <h1 className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold text-white`}>
              🏷️ Gestão de Categorias
            </h1>
          </div>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="bg-gradient-to-r from-green-600 to-green-700 text-white px-6 py-3 rounded-lg hover:from-green-700 hover:to-green-800 transition-all duration-300"
          >
            ➕ Nova Categoria
          </button>
        </div>

        {showAddForm && (
          <div className="bg-gray-800/50 rounded-2xl p-8 mb-8 border border-purple-500/30">
            <h3 className="text-2xl font-bold mb-6 text-white">➕ Nova Categoria</h3>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Nome da Categoria</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                    placeholder="Geek, Terror, etc."
                  />
                </div>
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Emoji</label>
                  <input
                    type="text"
                    value={formData.emoji}
                    onChange={(e) => setFormData({...formData, emoji: e.target.value})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                    placeholder="🤓"
                  />
                </div>
              </div>

              <div>
                <label className="block text-lg font-medium mb-3 text-gray-300">Descrição</label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  required
                  className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                  placeholder="Produtos relacionados com..."
                />
              </div>

              <div>
                <label className="block text-lg font-medium mb-3 text-gray-300">Cor da Categoria</label>
                <input
                  type="color"
                  value={formData.color}
                  onChange={(e) => setFormData({...formData, color: e.target.value})}
                  className="w-32 h-12 bg-gray-700 border border-purple-500/30 rounded-lg focus:border-purple-400 focus:outline-none"
                />
              </div>

              <div className="flex gap-4">
                <button
                  type="submit"
                  className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-8 py-3 rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all duration-300"
                >
                  ➕ Criar Categoria
                </button>
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="bg-gray-600 text-white px-8 py-3 rounded-lg hover:bg-gray-700 transition-all duration-300"
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        )}

        {loading ? (
          <div className="text-center text-white">
            <div className="animate-spin text-6xl mb-4">🔮</div>
            <p>Carregando categorias...</p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {categories.map((category) => (
              <div key={category.id} className="bg-gray-800/50 rounded-2xl border border-purple-500/30 p-6 text-center hover:border-purple-400 transition-colors duration-300">
                <div className="text-6xl mb-4">{category.emoji}</div>
                <h3 className="text-xl font-semibold text-white mb-2">{category.name}</h3>
                <p className="text-gray-300 text-sm mb-4">{category.description}</p>
                <div 
                  className="w-full h-4 rounded-full mb-4"
                  style={{ backgroundColor: category.color }}
                ></div>
                <div className="text-xs text-gray-400 mb-4">
                  ID: {category.id}
                </div>
                <button
                  onClick={() => handleDeleteCategory(category.id, category.name)}
                  className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm transition-colors duration-300 flex items-center justify-center w-full"
                >
                  🗑️ Remover Categoria
                </button>
              </div>
            ))}
          </div>
        )}

        {categories.length === 0 && !loading && (
          <div className="text-center py-12 text-gray-400">
            <div className="text-6xl mb-4">🏷️</div>
            <p>Nenhuma categoria encontrada</p>
          </div>
        )}
      </div>
    </div>
  );
};

const AdminEmails = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [emailForm, setEmailForm] = useState({
    type: 'discount',
    user_email: '',
    user_name: '',
    coupon_code: '',
    discount_value: '',
    discount_type: 'percentage',
    expiry_date: ''
  });
  const [sending, setSending] = useState(false);
  const { user } = useDeviceContext();
  const isMobile = useIsMobile();

  useEffect(() => {
    if (user?.is_admin) {
      loadUsers();
    }
  }, [user]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/admin/users`);
      setUsers(response.data);
    } catch (error) {
      console.error('Error loading users:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSendEmail = async (e) => {
    e.preventDefault();
    setSending(true);

    try {
      if (emailForm.type === 'discount') {
        const params = new URLSearchParams({
          user_email: emailForm.user_email,
          user_name: emailForm.user_name,
          coupon_code: emailForm.coupon_code,
          discount_value: parseFloat(emailForm.discount_value),
          discount_type: emailForm.discount_type,
          expiry_date: emailForm.expiry_date
        });
        await axios.post(`${API}/admin/emails/send-discount?${params}`);
      } else if (emailForm.type === 'birthday') {
        const params = new URLSearchParams({
          user_email: emailForm.user_email,
          user_name: emailForm.user_name,
          coupon_code: emailForm.coupon_code,
          discount_value: parseFloat(emailForm.discount_value)
        });
        await axios.post(`${API}/admin/emails/send-birthday?${params}`);
      }

      alert('Email enviado com sucesso!');
      setEmailForm({
        type: 'discount',
        user_email: '',
        user_name: '',
        coupon_code: '',
        discount_value: '',
        discount_type: 'percentage',
        expiry_date: ''
      });
    } catch (error) {
      alert('Erro ao enviar email');
    } finally {
      setSending(false);
    }
  };

  const handleUserSelect = (selectedUser) => {
    setEmailForm({
      ...emailForm,
      user_email: selectedUser.email,
      user_name: selectedUser.name
    });
  };

  if (!user?.is_admin) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black flex items-center justify-center">
        <div className="text-center text-white">
          <div className="text-8xl mb-4">🚫</div>
          <h1 className="text-4xl font-bold mb-4">Acesso Negado</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <div className="flex items-center mb-8">
          <Link to="/admin" className="text-purple-400 hover:text-purple-300 mr-4">
            ← Voltar ao Admin
          </Link>
          <h1 className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold text-white`}>
            📧 Gestão de Emails
          </h1>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Email Form */}
          <div className="bg-gray-800/50 rounded-2xl p-8 border border-purple-500/30">
            <h3 className="text-2xl font-bold mb-6 text-white">📧 Enviar Email</h3>
            
            <form onSubmit={handleSendEmail} className="space-y-6">
              <div>
                <label className="block text-lg font-medium mb-3 text-gray-300">Tipo de Email</label>
                <select
                  value={emailForm.type}
                  onChange={(e) => setEmailForm({...emailForm, type: e.target.value})}
                  className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                >
                  <option value="discount">Email de Desconto</option>
                  <option value="birthday">Email de Aniversário</option>
                </select>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Email do Utilizador</label>
                  <input
                    type="email"
                    value={emailForm.user_email}
                    onChange={(e) => setEmailForm({...emailForm, user_email: e.target.value})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                    placeholder="user@exemplo.com"
                  />
                </div>
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Nome do Utilizador</label>
                  <input
                    type="text"
                    value={emailForm.user_name}
                    onChange={(e) => setEmailForm({...emailForm, user_name: e.target.value})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                    placeholder="João Silva"
                  />
                </div>
              </div>

              <div className="grid md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Código do Cupão</label>
                  <input
                    type="text"
                    value={emailForm.coupon_code}
                    onChange={(e) => setEmailForm({...emailForm, coupon_code: e.target.value.toUpperCase()})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                    placeholder="DESCONTO20"
                  />
                </div>
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Valor do Desconto</label>
                  <input
                    type="number"
                    step="0.01"
                    value={emailForm.discount_value}
                    onChange={(e) => setEmailForm({...emailForm, discount_value: e.target.value})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                    placeholder="20"
                  />
                </div>
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Tipo</label>
                  <select
                    value={emailForm.discount_type}
                    onChange={(e) => setEmailForm({...emailForm, discount_type: e.target.value})}
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                  >
                    <option value="percentage">Percentagem</option>
                    <option value="fixed">Valor Fixo</option>
                  </select>
                </div>
              </div>

              {emailForm.type === 'discount' && (
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Data de Expiração</label>
                  <input
                    type="date"
                    value={emailForm.expiry_date}
                    onChange={(e) => setEmailForm({...emailForm, expiry_date: e.target.value})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                  />
                </div>
              )}

              <button
                type="submit"
                disabled={sending}
                className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-3 rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all duration-300 disabled:opacity-50"
              >
                {sending ? (
                  <span className="flex items-center justify-center">
                    <div className="animate-spin mr-2">📧</div>
                    Enviando...
                  </span>
                ) : (
                  '📧 Enviar Email'
                )}
              </button>
            </form>
          </div>

          {/* Users List */}
          <div className="bg-gray-800/50 rounded-2xl p-8 border border-purple-500/30">
            <h3 className="text-2xl font-bold mb-6 text-white">👥 Selecionar Utilizador</h3>
            
            {loading ? (
              <div className="text-center text-white">
                <div className="animate-spin text-4xl mb-4">🔮</div>
                <p>Carregando utilizadores...</p>
              </div>
            ) : (
              <div className="max-h-96 overflow-y-auto space-y-3">
                {users.map((userItem) => (
                  <div
                    key={userItem.id}
                    onClick={() => handleUserSelect(userItem)}
                    className="p-4 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors duration-300 cursor-pointer"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-white font-semibold">{userItem.name}</h4>
                        <p className="text-gray-400 text-sm">{userItem.email}</p>
                      </div>
                      {userItem.is_admin && (
                        <span className="text-purple-400 text-xs">⚙️ Admin</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const AdminPromotions = () => {
  const [promotions, setPromotions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingPromotion, setEditingPromotion] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    discount_type: 'percentage',
    discount_value: '',
    valid_from: '',
    valid_until: ''
  });
  const { user } = useDeviceContext();
  const isMobile = useIsMobile();

  useEffect(() => {
    if (user?.is_admin) {
      loadPromotions();
    }
  }, [user]);

  const loadPromotions = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/admin/promotions`);
      setPromotions(response.data);
    } catch (error) {
      console.error('Error loading promotions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const promotionData = {
        ...formData,
        discount_value: parseFloat(formData.discount_value),
        valid_from: new Date(formData.valid_from).toISOString(),
        valid_until: new Date(formData.valid_until).toISOString()
      };

      if (editingPromotion) {
        await axios.put(`${API}/admin/promotions/${editingPromotion.id}`, promotionData);
        alert('Promoção atualizada com sucesso!');
      } else {
        await axios.post(`${API}/admin/promotions`, promotionData);
        alert('Promoção criada com sucesso!');
      }

      setFormData({
        name: '',
        description: '',
        discount_type: 'percentage',
        discount_value: '',
        valid_from: '',
        valid_until: ''
      });
      setShowAddForm(false);
      setEditingPromotion(null);
      loadPromotions();
    } catch (error) {
      alert('Erro ao salvar promoção');
    }
  };

  const handleEdit = (promotion) => {
    setEditingPromotion(promotion);
    setFormData({
      name: promotion.name,
      description: promotion.description,
      discount_type: promotion.discount_type,
      discount_value: promotion.discount_value.toString(),
      valid_from: promotion.valid_from ? new Date(promotion.valid_from).toISOString().split('T')[0] : '',
      valid_until: promotion.valid_until ? new Date(promotion.valid_until).toISOString().split('T')[0] : ''
    });
    setShowAddForm(true);
  };

  const handleDelete = async (promotionId) => {
    if (window.confirm('Tem certeza que quer desativar esta promoção?')) {
      try {
        await axios.delete(`${API}/admin/promotions/${promotionId}`);
        alert('Promoção desativada!');
        loadPromotions();
      } catch (error) {
        alert('Erro ao desativar promoção');
      }
    }
  };

  if (!user?.is_admin) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black flex items-center justify-center">
        <div className="text-center text-white">
          <div className="text-8xl mb-4">🚫</div>
          <h1 className="text-4xl font-bold mb-4">Acesso Negado</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center">
            <Link to="/admin" className="text-purple-400 hover:text-purple-300 mr-4">
              ← Voltar ao Admin
            </Link>
            <h1 className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold text-white`}>
              🏷️ Gestão de Promoções
            </h1>
          </div>
          <button
            onClick={() => {
              setShowAddForm(!showAddForm);
              setEditingPromotion(null);
              setFormData({
                name: '',
                description: '',
                discount_type: 'percentage',
                discount_value: '',
                valid_from: '',
                valid_until: ''
              });
            }}
            className="bg-gradient-to-r from-green-600 to-green-700 text-white px-6 py-3 rounded-lg hover:from-green-700 hover:to-green-800 transition-all duration-300"
          >
            ➕ Nova Promoção
          </button>
        </div>

        {showAddForm && (
          <div className="bg-gray-800/50 rounded-2xl p-8 mb-8 border border-purple-500/30">
            <h3 className="text-2xl font-bold mb-6 text-white">
              {editingPromotion ? '✏️ Editar Promoção' : '➕ Nova Promoção'}
            </h3>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Nome da Promoção</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                    placeholder="Promoção de Verão"
                  />
                </div>
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Tipo de Desconto</label>
                  <select
                    value={formData.discount_type}
                    onChange={(e) => setFormData({...formData, discount_type: e.target.value})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                  >
                    <option value="percentage">Percentagem (%)</option>
                    <option value="fixed">Valor Fixo (€)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-lg font-medium mb-3 text-gray-300">Descrição</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  required
                  rows="3"
                  className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                  placeholder="Descrição da promoção..."
                />
              </div>

              <div>
                <label className="block text-lg font-medium mb-3 text-gray-300">
                  Valor do Desconto {formData.discount_type === 'percentage' ? '(%)' : '(€)'}
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.discount_value}
                  onChange={(e) => setFormData({...formData, discount_value: e.target.value})}
                  required
                  className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                  placeholder={formData.discount_type === 'percentage' ? '25' : '10.00'}
                />
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Válido De</label>
                  <input
                    type="date"
                    value={formData.valid_from}
                    onChange={(e) => setFormData({...formData, valid_from: e.target.value})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Válido Até</label>
                  <input
                    type="date"
                    value={formData.valid_until}
                    onChange={(e) => setFormData({...formData, valid_until: e.target.value})}
                    required
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex gap-4">
                <button
                  type="submit"
                  className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-8 py-3 rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all duration-300"
                >
                  {editingPromotion ? '💾 Atualizar' : '➕ Criar'} Promoção
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowAddForm(false);
                    setEditingPromotion(null);
                  }}
                  className="bg-gray-600 text-white px-8 py-3 rounded-lg hover:bg-gray-700 transition-all duration-300"
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        )}

        {loading ? (
          <div className="text-center text-white">
            <div className="animate-spin text-6xl mb-4">🔮</div>
            <p>Carregando promoções...</p>
          </div>
        ) : (
          <div className="bg-gray-800/50 rounded-2xl border border-purple-500/30 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-white">
                <thead className="bg-purple-900/50">
                  <tr>
                    <th className="text-left p-4">Nome</th>
                    <th className="text-left p-4">Descrição</th>
                    <th className="text-left p-4">Desconto</th>
                    <th className="text-left p-4">Validade</th>
                    <th className="text-left p-4">Status</th>
                    <th className="text-left p-4">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {promotions.map((promotion) => (
                    <tr key={promotion.id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                      <td className="p-4 font-semibold">{promotion.name}</td>
                      <td className="p-4 text-sm text-gray-300 max-w-xs truncate">{promotion.description}</td>
                      <td className="p-4 font-bold text-green-400">
                        {promotion.discount_type === 'percentage' 
                          ? `${promotion.discount_value}%` 
                          : `€${promotion.discount_value}`}
                      </td>
                      <td className="p-4 text-sm">
                        {new Date(promotion.valid_from).toLocaleDateString('pt-PT')} - {new Date(promotion.valid_until).toLocaleDateString('pt-PT')}
                      </td>
                      <td className="p-4">
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          promotion.is_active 
                            ? 'bg-green-900 text-green-300' 
                            : 'bg-red-900 text-red-300'
                        }`}>
                          {promotion.is_active ? 'Ativa' : 'Inativa'}
                        </span>
                      </td>
                      <td className="p-4">
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleEdit(promotion)}
                            className="text-blue-400 hover:text-blue-300 text-sm"
                          >
                            ✏️ Editar
                          </button>
                          <button
                            onClick={() => handleDelete(promotion.id)}
                            className="text-red-400 hover:text-red-300 text-sm"
                          >
                            🗑️ Desativar
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {promotions.length === 0 && (
              <div className="text-center py-12 text-gray-400">
                <div className="text-6xl mb-4">🏷️</div>
                <p>Nenhuma promoção encontrada</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Live Chat Components
const LiveChatButton = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isNewTicket, setIsNewTicket] = useState(false);
  const [pendingChats, setPendingChats] = useState(0);
  const { user } = useDeviceContext();

  // Check for pending chats if user is admin
  useEffect(() => {
    if (user?.is_admin) {
      checkPendingChats();
      const interval = setInterval(checkPendingChats, 5000); // Check every 5 seconds
      return () => clearInterval(interval);
    }
  }, [user]);

  const checkPendingChats = async () => {
    try {
      const response = await axios.get(`${API}/admin/chat/sessions`);
      const pendingCount = response.data.filter(session => 
        session.status === 'pending' && !session.agent_id
      ).length;
      setPendingChats(pendingCount);
    } catch (error) {
      console.error('Error checking pending chats:', error);
    }
  };

  if (!user) return null;

  return (
    <>
      {/* Chat Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 bg-gradient-to-r from-purple-600 to-pink-600 text-white p-4 rounded-full shadow-2xl hover:from-purple-700 hover:to-pink-700 transition-all duration-300 transform hover:scale-110 z-50 relative"
      >
        💬
        {user.is_admin && pendingChats > 0 && (
          <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full min-w-[20px] h-5 flex items-center justify-center font-bold animate-pulse">
            {pendingChats}
          </span>
        )}
      </button>

      {/* Chat Modal */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-2xl w-full max-w-md border border-purple-500/30">
            <div className="flex items-center justify-between p-4 border-b border-purple-500/30">
              <h3 className="text-lg font-semibold text-white">
                💬 Live Chat
                {user.is_admin && pendingChats > 0 && (
                  <span className="ml-2 bg-red-500 text-white text-xs px-2 py-1 rounded-full">
                    {pendingChats} pendentes
                  </span>
                )}
              </h3>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-white"
              >
                ✕
              </button>
            </div>
            
            {user.is_admin ? (
              <div className="p-6">
                <Link
                  to="/admin/chat"
                  onClick={() => setIsOpen(false)}
                  className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-3 rounded-lg font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-300 text-center block"
                >
                  🎫 Gerir Chats ({pendingChats} pendentes)
                </Link>
              </div>
            ) : !isNewTicket ? (
              <NewChatForm onSubmit={() => setIsNewTicket(true)} onClose={() => setIsOpen(false)} />
            ) : (
              <ChatInterface onClose={() => setIsOpen(false)} />
            )}
          </div>
        </div>
      )}
    </>
  );
};

const NewChatForm = ({ onSubmit, onClose }) => {
  const [formData, setFormData] = useState({
    name: '',
    reason: ''
  });
  const { user } = useDeviceContext();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(`${API}/chat/sessions`, {
        client_name: formData.name,
        reason: formData.reason
      });
      onSubmit();
    } catch (error) {
      console.error('Error creating chat session:', error);
      alert('Erro ao criar sessão de chat');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-6 space-y-4">
      <div>
        <label className="block text-sm font-medium mb-2 text-gray-300">Nome</label>
        <input
          type="text"
          value={formData.name}
          onChange={(e) => setFormData({...formData, name: e.target.value})}
          required
          className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
          placeholder="Digite seu nome"
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium mb-2 text-gray-300">Motivo do Contacto</label>
        <textarea
          value={formData.reason}
          onChange={(e) => setFormData({...formData, reason: e.target.value})}
          required
          className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 h-24 focus:border-purple-400 focus:outline-none resize-none"
          placeholder="Descreva o motivo do seu contacto"
        />
      </div>
      
      <div className="flex space-x-3">
        <button
          type="submit"
          className="flex-1 bg-gradient-to-r from-purple-600 to-pink-600 text-white py-3 rounded-lg font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-300"
        >
          Iniciar Chat
        </button>
        <button
          type="button"
          onClick={onClose}
          className="px-6 py-3 text-gray-400 hover:text-white transition-colors duration-300"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
};

const ChatInterface = ({ onClose }) => {
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [sessionId, setSessionId] = useState(null);

  useEffect(() => {
    // Load chat session and messages
    loadChatSession();
  }, []);

  const loadChatSession = async () => {
    try {
      const response = await axios.get(`${API}/chat/sessions`);
      if (response.data.length > 0) {
        const session = response.data[0];
        setSessionId(session.id);
        loadMessages(session.id);
      }
    } catch (error) {
      console.error('Error loading chat session:', error);
    }
  };

  const loadMessages = async (id) => {
    try {
      const response = await axios.get(`${API}/chat/sessions/${id}/messages`);
      setMessages(response.data);
    } catch (error) {
      console.error('Error loading messages:', error);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !sessionId) return;

    try {
      await axios.post(`${API}/chat/sessions/${sessionId}/messages`, {
        content: newMessage
      });
      setNewMessage('');
      loadMessages(sessionId);
    } catch (error) {
      console.error('Error sending message:', error);
    }
  };

  return (
    <div className="flex flex-col h-96">
      <div className="flex-1 p-4 overflow-y-auto space-y-3">
        {messages.length === 0 ? (
          <div className="text-center text-gray-400 py-8">
            <p>🔄 Aguardando agente...</p>
            <p className="text-sm mt-2">Um agente irá atendê-lo em breve</p>
          </div>
        ) : (
          messages.map((message, index) => (
            <div key={index} className={`flex ${message.sender_type === 'client' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-xs px-4 py-2 rounded-lg ${
                message.sender_type === 'client' 
                  ? 'bg-purple-600 text-white' 
                  : 'bg-gray-700 text-white'
              }`}>
                <p className="text-sm">{message.content}</p>
                <p className="text-xs opacity-70 mt-1">
                  {new Date(message.created_at).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
      
      <form onSubmit={sendMessage} className="p-4 border-t border-purple-500/30">
        <div className="flex space-x-2">
          <input
            type="text"
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            className="flex-1 bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-2 focus:border-purple-400 focus:outline-none"
            placeholder="Digite sua mensagem..."
          />
          <button
            type="submit"
            className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-4 py-2 rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all duration-300"
          >
            ➤
          </button>
        </div>
      </form>
    </div>
  );
};

// Admin Chat Management
const AdminChatDashboard = () => {
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [newTicketSound, setNewTicketSound] = useState(null);
  const { user } = useDeviceContext();
  const isMobile = useIsMobile();

  useEffect(() => {
    if (user?.is_admin) {
      loadSessions();
      // Check for new tickets every 5 seconds
      const interval = setInterval(checkForNewTickets, 5000);
      return () => clearInterval(interval);
    }
  }, [user]);

  const loadSessions = async () => {
    try {
      const response = await axios.get(`${API}/admin/chat/sessions`);
      setSessions(response.data);
    } catch (error) {
      console.error('Error loading sessions:', error);
    }
  };

  const checkForNewTickets = async () => {
    try {
      const response = await axios.get(`${API}/admin/chat/sessions`);
      const newSessions = response.data;
      
      // Check if there are new unassigned sessions
      const newUnassigned = newSessions.filter(session => 
        !session.assigned_agent && 
        !sessions.find(s => s.id === session.id)
      );
      
      if (newUnassigned.length > 0) {
        playNotificationSound();
      }
      
      setSessions(newSessions);
    } catch (error) {
      console.error('Error checking for new tickets:', error);
    }
  };

  const playNotificationSound = () => {
    // Create a simple "plim" sound using Web Audio API
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.frequency.value = 800;
    oscillator.type = 'sine';
    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
    
    oscillator.start();
    oscillator.stop(audioContext.currentTime + 0.3);
  };

  const assignSession = async (sessionId, accept) => {
    try {
      if (accept) {
        await axios.put(`${API}/admin/chat/sessions/${sessionId}/assign`);
        alert('Sessão aceita com sucesso!');
      } else {
        await axios.put(`${API}/admin/chat/sessions/${sessionId}/reject`);
        alert('Sessão rejeitada.');
      }
      loadSessions();
    } catch (error) {
      console.error('Error assigning session:', error);
      alert('Erro ao processar sessão: ' + (error.response?.data?.detail || 'Erro desconhecido'));
    }
  };

  const closeSession = async (sessionId) => {
    if (!window.confirm('Tem certeza que quer fechar esta sessão?')) {
      return;
    }
    
    try {
      await axios.put(`${API}/admin/chat/sessions/${sessionId}/close`);
      alert('Sessão fechada com sucesso!');
      setSelectedSession(null);
      loadSessions();
    } catch (error) {
      console.error('Error closing session:', error);
      alert('Erro ao fechar sessão: ' + (error.response?.data?.detail || 'Erro desconhecido'));
    }
  };

  if (!user?.is_admin) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black flex items-center justify-center">
        <div className="text-center text-white">
          <div className="text-8xl mb-4">🚫</div>
          <h1 className="text-4xl font-bold mb-4">Acesso Negado</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <div className="flex items-center mb-8">
          <Link to="/admin" className="text-purple-400 hover:text-purple-300 mr-4">
            ← Voltar ao Admin
          </Link>
          <h1 className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold text-white`}>
            💬 Gestão de Chat
          </h1>
        </div>

        {/* Chat Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-yellow-900/30 border border-yellow-500/30 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-yellow-400">
              {sessions.filter(s => s.status === 'pending').length}
            </div>
            <div className="text-sm text-yellow-300">Pendentes</div>
          </div>
          <div className="bg-green-900/30 border border-green-500/30 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-green-400">
              {sessions.filter(s => s.status === 'active').length}
            </div>
            <div className="text-sm text-green-300">Ativos</div>
          </div>
          <div className="bg-red-900/30 border border-red-500/30 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-red-400">
              {sessions.filter(s => s.status === 'rejected').length}
            </div>
            <div className="text-sm text-red-300">Rejeitados</div>
          </div>
          <div className="bg-gray-900/30 border border-gray-500/30 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-gray-400">
              {sessions.filter(s => s.status === 'closed' || s.status === 'auto_closed').length}
            </div>
            <div className="text-sm text-gray-300">Fechados</div>
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Sessions List */}
          <div className="bg-gray-800/50 rounded-2xl p-8 border border-purple-500/30">
            <h3 className="text-2xl font-bold mb-6 text-white">🎫 Sessões de Chat</h3>
            
            <div className="space-y-4">
              {sessions.length === 0 ? (
                <p className="text-gray-400 text-center py-8">Nenhuma sessão de chat ativa</p>
              ) : (
                sessions.map(session => (
                  <div key={session.id} className={`p-4 rounded-lg border ${
                    session.status === 'active' && session.agent_id
                      ? 'bg-green-900/30 border-green-500/30' 
                      : session.status === 'pending'
                      ? 'bg-yellow-900/30 border-yellow-500/30'
                      : session.status === 'rejected'
                      ? 'bg-red-900/30 border-red-500/30'
                      : session.status === 'auto_closed'
                      ? 'bg-gray-900/30 border-gray-500/30'
                      : 'bg-blue-900/30 border-blue-500/30'
                  }`}>
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <h4 className="font-semibold text-white">
                          {session.user_name} ({session.user_email})
                        </h4>
                        <p className="text-sm text-gray-300 mb-1">
                          <strong>Assunto:</strong> {session.subject}
                        </p>
                        <div className="flex items-center space-x-4 text-xs text-gray-400">
                          <span>📅 {new Date(session.created_at).toLocaleString('pt-PT')}</span>
                          <span className={`px-2 py-1 rounded-full ${
                            session.status === 'active' ? 'bg-green-900 text-green-300' :
                            session.status === 'pending' ? 'bg-yellow-900 text-yellow-300' :
                            session.status === 'rejected' ? 'bg-red-900 text-red-300' :
                            session.status === 'auto_closed' ? 'bg-gray-900 text-gray-300' :
                            'bg-blue-900 text-blue-300'
                          }`}>
                            {session.status === 'active' ? '🟢 Ativo' :
                             session.status === 'pending' ? '🟡 Pendente' :
                             session.status === 'rejected' ? '🔴 Rejeitado' :
                             session.status === 'auto_closed' ? '⚫ Auto-fechado' :
                             session.status}
                          </span>
                        </div>
                      </div>
                      
                      {session.status === 'pending' ? (
                        <div className="flex space-x-2 ml-4">
                          <button
                            onClick={() => assignSession(session.id, true)}
                            className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm transition-colors duration-300"
                          >
                            ✓ Aceitar
                          </button>
                          <button
                            onClick={() => assignSession(session.id, false)}
                            className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm transition-colors duration-300"
                          >
                            ✗ Rejeitar
                          </button>
                        </div>
                      ) : session.status === 'active' && session.agent_id ? (
                        <div className="flex space-x-2 ml-4">
                          <button
                            onClick={() => setSelectedSession(session)}
                            className="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded text-sm transition-colors duration-300"
                          >
                            💬 Abrir Chat
                          </button>
                          <button
                            onClick={() => closeSession(session.id)}
                            className="bg-gray-600 hover:bg-gray-700 text-white px-3 py-1 rounded text-sm transition-colors duration-300"
                          >
                            🔒 Fechar
                          </button>
                        </div>
                      ) : null}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Chat Interface */}
          {selectedSession && (
            <div className="bg-gray-800/50 rounded-2xl p-8 border border-purple-500/30">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-2xl font-bold text-white">
                  💬 Chat com {selectedSession.client_name}
                </h3>
                <button
                  onClick={() => setSelectedSession(null)}
                  className="text-gray-400 hover:text-white"
                >
                  ✕
                </button>
              </div>
              
              <AdminChatInterface session={selectedSession} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const AdminChatInterface = ({ session }) => {
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');

  useEffect(() => {
    loadMessages();
    const interval = setInterval(loadMessages, 2000);
    return () => clearInterval(interval);
  }, [session.id]);

  const loadMessages = async () => {
    try {
      const response = await axios.get(`${API}/chat/sessions/${session.id}/messages`);
      setMessages(response.data);
    } catch (error) {
      console.error('Error loading messages:', error);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim()) return;

    try {
      await axios.post(`${API}/chat/sessions/${session.id}/messages`, {
        content: newMessage
      });
      setNewMessage('');
      loadMessages();
    } catch (error) {
      console.error('Error sending message:', error);
    }
  };

  return (
    <div className="flex flex-col h-96">
      <div className="flex-1 overflow-y-auto space-y-3 mb-4">
        {messages.map((message, index) => (
          <div key={index} className={`flex ${message.sender_type === 'agent' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-xs px-4 py-2 rounded-lg ${
              message.sender_type === 'agent' 
                ? 'bg-purple-600 text-white' 
                : 'bg-gray-700 text-white'
            }`}>
              <p className="text-sm">{message.content}</p>
              <p className="text-xs opacity-70 mt-1">
                {new Date(message.created_at).toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}
      </div>
      
      <form onSubmit={sendMessage}>
        <div className="flex space-x-2">
          <input
            type="text"
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            className="flex-1 bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-2 focus:border-purple-400 focus:outline-none"
            placeholder="Digite sua mensagem..."
          />
          <button
            type="submit"
            className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-4 py-2 rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all duration-300"
          >
            ➤
          </button>
        </div>
      </form>
    </div>
  );
};

// User Profile Page
const UserProfile = () => {
  const [profileData, setProfileData] = useState({
    name: '',
    email: '',
    phone: '',
    street: '',
    postalCode: '',
    city: '',
    birthDate: ''
  });
  const [orders, setOrders] = useState([]);
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
    otpCode: ''
  });
  const [otpSent, setOtpSent] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { user, setUser } = useDeviceContext();
  const isMobile = useIsMobile();

  useEffect(() => {
    if (user) {
      loadProfileData();
      loadOrders();
    }
  }, [user]);

  const loadProfileData = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setProfileData(response.data);
    } catch (error) {
      console.error('Error loading profile:', error);
    }
  };

  const loadOrders = async () => {
    try {
      const response = await axios.get(`${API}/auth/orders`);
      setOrders(response.data);
    } catch (error) {
      console.error('Error loading orders:', error);
    }
  };

  const updateProfile = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await axios.put(`${API}/auth/profile`, profileData);
      setUser(response.data);
      alert('Perfil atualizado com sucesso!');
    } catch (error) {
      alert('Erro ao atualizar perfil');
    } finally {
      setIsLoading(false);
    }
  };

  const sendOtp = async () => {
    setIsLoading(true);
    try {
      await axios.post(`${API}/auth/send-otp`, {
        email: user.email
      });
      setOtpSent(true);
      alert('Código OTP enviado para seu email!');
    } catch (error) {
      alert('Erro ao enviar OTP');
    } finally {
      setIsLoading(false);
    }
  };

  const changePassword = async (e) => {
    e.preventDefault();
    
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      alert('As senhas não coincidem');
      return;
    }

    setIsLoading(true);
    try {
      await axios.post(`${API}/auth/change-password`, {
        current_password: passwordData.currentPassword,
        new_password: passwordData.newPassword,
        otp_code: passwordData.otpCode
      });
      
      alert('Senha alterada com sucesso!');
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: '',
        otpCode: ''
      });
      setOtpSent(false);
    } catch (error) {
      alert(error.response?.data?.detail || 'Erro ao alterar senha');
    } finally {
      setIsLoading(false);
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black flex items-center justify-center">
        <div className="text-center text-white">
          <h1 className="text-4xl font-bold mb-4">Acesso Negado</h1>
          <p>Faça login para aceder ao seu perfil</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <h1 className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold mb-12 text-center text-white`}>
          👤 Meu Perfil
        </h1>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Profile Information */}
          <div className="bg-gray-800/50 rounded-2xl p-8 border border-purple-500/30">
            <h3 className="text-2xl font-bold mb-6 text-white">📝 Informações Pessoais</h3>
            
            <form onSubmit={updateProfile} className="space-y-6">
              <div>
                <label className="block text-lg font-medium mb-3 text-gray-300">Nome</label>
                <input
                  type="text"
                  value={profileData.name}
                  onChange={(e) => setProfileData({...profileData, name: e.target.value})}
                  className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                />
              </div>
              
              <div>
                <label className="block text-lg font-medium mb-3 text-gray-300">Email</label>
                <input
                  type="email"
                  value={profileData.email}
                  disabled
                  className="w-full bg-gray-600 text-gray-300 border border-purple-500/30 rounded-lg px-4 py-3 cursor-not-allowed"
                />
              </div>
              
              <div>
                <label className="block text-lg font-medium mb-3 text-gray-300">Telemóvel</label>
                <input
                  type="tel"
                  value={profileData.phone || ''}
                  onChange={(e) => setProfileData({...profileData, phone: e.target.value})}
                  className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                  placeholder="+351 xxx xxx xxx"
                />
              </div>
              
              <div>
                <label className="block text-lg font-medium mb-3 text-gray-300">Endereço</label>
                <input
                  type="text"
                  value={profileData.street || ''}
                  onChange={(e) => setProfileData({...profileData, street: e.target.value})}
                  className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                  placeholder="Rua e número da porta"
                />
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Código Postal</label>
                  <input
                    type="text"
                    value={profileData.postalCode || ''}
                    onChange={(e) => {
                      const value = e.target.value.replace(/[^\d-]/g, '');
                      if (value.length <= 8) {
                        let formatted = value;
                        if (value.length > 4 && !value.includes('-')) {
                          formatted = value.slice(0, 4) + '-' + value.slice(4);
                        }
                        setProfileData({...profileData, postalCode: formatted});
                      }
                    }}
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                    placeholder="1234-567"
                    maxLength="8"
                  />
                </div>
                <div>
                  <label className="block text-lg font-medium mb-3 text-gray-300">Localidade</label>
                  <input
                    type="text"
                    value={profileData.city || ''}
                    onChange={(e) => setProfileData({...profileData, city: e.target.value})}
                    className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                    placeholder="Lisboa"
                  />
                </div>
              </div>

              <div>
                <label className="block text-lg font-medium mb-3 text-gray-300">Data de Nascimento</label>
                <input
                  type="date"
                  value={profileData.birthDate || ''}
                  onChange={(e) => setProfileData({...profileData, birthDate: e.target.value})}
                  className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                />
              </div>
              
              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-3 rounded-lg font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-300 disabled:opacity-50"
              >
                {isLoading ? 'Atualizando...' : 'Atualizar Perfil'}
              </button>
            </form>
          </div>

          {/* Password Change */}
          <div className="bg-gray-800/50 rounded-2xl p-8 border border-purple-500/30">
            <h3 className="text-2xl font-bold mb-6 text-white">🔒 Alterar Senha</h3>
            
            <form onSubmit={changePassword} className="space-y-6">
              <div>
                <label className="block text-lg font-medium mb-3 text-gray-300">Senha Atual</label>
                <input
                  type="password"
                  value={passwordData.currentPassword}
                  onChange={(e) => setPasswordData({...passwordData, currentPassword: e.target.value})}
                  className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                />
              </div>
              
              <div>
                <label className="block text-lg font-medium mb-3 text-gray-300">Nova Senha</label>
                <input
                  type="password"
                  value={passwordData.newPassword}
                  onChange={(e) => setPasswordData({...passwordData, newPassword: e.target.value})}
                  className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                />
              </div>
              
              <div>
                <label className="block text-lg font-medium mb-3 text-gray-300">Confirmar Nova Senha</label>
                <input
                  type="password"
                  value={passwordData.confirmPassword}
                  onChange={(e) => setPasswordData({...passwordData, confirmPassword: e.target.value})}
                  className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                />
              </div>
              
              {!otpSent ? (
                <button
                  type="button"
                  onClick={sendOtp}
                  disabled={isLoading}
                  className="w-full bg-yellow-600 hover:bg-yellow-700 text-white py-3 rounded-lg font-semibold transition-all duration-300 disabled:opacity-50"
                >
                  {isLoading ? 'Enviando...' : 'Enviar Código OTP'}
                </button>
              ) : (
                <>
                  <div>
                    <label className="block text-lg font-medium mb-3 text-gray-300">Código OTP</label>
                    <input
                      type="text"
                      value={passwordData.otpCode}
                      onChange={(e) => setPasswordData({...passwordData, otpCode: e.target.value})}
                      className="w-full bg-gray-700 text-white border border-purple-500/30 rounded-lg px-4 py-3 focus:border-purple-400 focus:outline-none"
                      placeholder="Digite o código recebido no email"
                    />
                  </div>
                  
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-3 rounded-lg font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-300 disabled:opacity-50"
                  >
                    {isLoading ? 'Alterando...' : 'Alterar Senha'}
                  </button>
                </>
              )}
            </form>
          </div>
        </div>

        {/* Order History */}
        <div className="mt-12 bg-gray-800/50 rounded-2xl p-8 border border-purple-500/30">
          <h3 className="text-2xl font-bold mb-6 text-white">📦 Histórico de Encomendas</h3>
          
          {orders.length === 0 ? (
            <p className="text-gray-400 text-center py-8">Ainda não fez nenhuma encomenda</p>
          ) : (
            <div className="space-y-4">
              {orders.map(order => (
                <div key={order.id} className="bg-gray-700/50 rounded-lg p-6 border border-purple-500/20">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="font-semibold text-white">Encomenda #{order.id.slice(0, 8)}</h4>
                    <span className={`px-3 py-1 rounded-full text-sm ${
                      order.status === 'completed' ? 'bg-green-900/50 text-green-300' :
                      order.status === 'processing' ? 'bg-yellow-900/50 text-yellow-300' :
                      'bg-gray-900/50 text-gray-300'
                    }`}>
                      {order.status}
                    </span>
                  </div>
                  
                  <div className="grid md:grid-cols-2 gap-4 text-sm text-gray-300">
                    <div>
                      <p><strong>Data:</strong> {new Date(order.created_at).toLocaleDateString()}</p>
                      <p><strong>Total:</strong> €{order.total}</p>
                    </div>
                    <div>
                      <p><strong>Produtos:</strong> {order.items?.length || 0}</p>
                      <p><strong>Pagamento:</strong> {order.payment_method}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// FAQ Component
const FAQ = () => {
  const isMobile = useIsMobile();
  const [openQuestions, setOpenQuestions] = useState({});

  const faqData = [
    {
      question: "O que são as Mystery Boxes?",
      answer: "As Mystery Boxes são caixas surpresa que contêm produtos selecionados cuidadosamente dentro de uma temática específica. Cada caixa é uma aventura única com itens que podem valer muito mais do que o preço pago!"
    },
    {
      question: "Como funcionam as assinaturas?",
      answer: "Com as assinaturas, recebes uma Mystery Box regularmente (mensal, trimestral ou anual) com desconto especial. Podes pausar ou cancelar a qualquer momento através do teu perfil."
    },
    {
      question: "Posso escolher os produtos da minha Mystery Box?",
      answer: "Não, essa é a magia! Os produtos são selecionados pela nossa equipa para garantir surpresas incríveis. Podes escolher a categoria temática, mas os produtos específicos são sempre uma surpresa."
    },
    {
      question: "Qual é a política de devolução?",
      answer: "Devido à natureza surpresa dos nossos produtos, não aceitamos devoluções, exceto em casos de produtos danificados durante o transporte. Nestes casos, contacta-nos em 48h após a receção."
    },
    {
      question: "Quanto tempo demora a entrega?",
      answer: "As entregas são realizadas entre 3-5 dias úteis para Portugal Continental. Ilhas e outros destinos podem demorar 7-10 dias úteis."
    },
    {
      question: "Posso oferecer uma Mystery Box?",
      answer: "Claro! Podes comprar uma Mystery Box como presente. Durante o checkout, simplesmente indica o endereço de entrega do destinatário."
    },
    {
      question: "Como contactar o apoio ao cliente?",
      answer: "Podes usar o chat ao vivo no canto inferior direito da página, enviar email para suporte@mysteryboxstore.pt ou ligar para +351 123 456 789."
    },
    {
      question: "Há garantia de qualidade dos produtos?",
      answer: "Sim! Todos os produtos são verificados pela nossa equipa antes do envio. Trabalhamos apenas com fornecedores de confiança para garantir a melhor qualidade."
    }
  ];

  const toggleQuestion = (index) => {
    setOpenQuestions(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <div className="text-center mb-12">
          <h1 className={`${isMobile ? 'text-3xl' : 'text-5xl'} font-bold text-white mb-6`}>
            ❓ Perguntas Frequentes
          </h1>
          <p className={`${isMobile ? 'text-lg' : 'text-xl'} text-gray-300 max-w-2xl mx-auto`}>
            Encontra respostas para as dúvidas mais comuns sobre as nossas Mystery Boxes
          </p>
        </div>

        <div className="max-w-4xl mx-auto space-y-4">
          {faqData.map((faq, index) => (
            <div key={index} className="bg-gray-800/50 rounded-2xl border border-purple-500/30 overflow-hidden">
              <button
                onClick={() => toggleQuestion(index)}
                className="w-full text-left p-6 hover:bg-gray-700/30 transition-colors duration-300 flex items-center justify-between"
              >
                <h3 className={`${isMobile ? 'text-lg' : 'text-xl'} font-semibold text-white pr-4`}>
                  {faq.question}
                </h3>
                <span className={`text-purple-400 text-2xl transform transition-transform duration-300 ${openQuestions[index] ? 'rotate-180' : ''}`}>
                  ▼
                </span>
              </button>
              
              {openQuestions[index] && (
                <div className="px-6 pb-6 border-t border-purple-500/20">
                  <p className={`${isMobile ? 'text-base' : 'text-lg'} text-gray-300 leading-relaxed pt-4`}>
                    {faq.answer}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="text-center mt-12">
          <div className="bg-gray-800/50 rounded-2xl p-8 border border-purple-500/30 inline-block">
            <h3 className={`${isMobile ? 'text-xl' : 'text-2xl'} font-bold text-white mb-4`}>
              Não encontraste a resposta?
            </h3>
            <p className="text-gray-300 mb-6">
              A nossa equipa está aqui para ajudar! Contacta-nos através do chat ao vivo.
            </p>
            <div className="flex items-center justify-center space-x-4">
              <div className="flex items-center text-purple-400">
                <span className="mr-2">💬</span>
                <span>Chat ao vivo</span>
              </div>
              <div className="flex items-center text-purple-400">
                <span className="mr-2">📧</span>
                <span>suporte@mysteryboxstore.pt</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Terms and Conditions Component
const TermsAndConditions = () => {
  const isMobile = useIsMobile();

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <div className="text-center mb-12">
          <h1 className={`${isMobile ? 'text-3xl' : 'text-5xl'} font-bold text-white mb-6`}>
            📋 Termos e Condições
          </h1>
          <p className={`${isMobile ? 'text-lg' : 'text-xl'} text-gray-300`}>
            Última atualização: {new Date().toLocaleDateString('pt-PT')}
          </p>
        </div>

        <div className="max-w-4xl mx-auto bg-gray-800/50 rounded-2xl p-8 border border-purple-500/30">
          <div className="prose prose-invert max-w-none">
            <section className="mb-8">
              <h2 className="text-2xl font-bold text-white mb-4">1. Definições e Interpretação</h2>
              <p className="text-gray-300 mb-4">
                Os presentes termos e condições regem o uso do website Mystery Box Store e a compra de produtos através do mesmo.
                Ao utilizar os nossos serviços, aceitas integralmente estes termos.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-white mb-4">2. Produtos e Serviços</h2>
              <div className="text-gray-300 space-y-3">
                <p><strong>2.1 Mystery Boxes:</strong> Os produtos incluídos nas Mystery Boxes são selecionados pela nossa equipa e podem variar. Não garantimos produtos específicos.</p>
                <p><strong>2.2 Disponibilidade:</strong> Os produtos estão sujeitos a disponibilidade de stock.</p>
                <p><strong>2.3 Preços:</strong> Todos os preços incluem IVA à taxa legal em vigor. Reservamo-nos o direito de alterar preços sem aviso prévio.</p>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-white mb-4">3. Encomendas e Pagamento</h2>
              <div className="text-gray-300 space-y-3">
                <p><strong>3.1 Processamento:</strong> As encomendas são processadas após confirmação do pagamento.</p>
                <p><strong>3.2 Métodos de Pagamento:</strong> Aceitamos cartão de crédito/débito, transferência bancária e pagamento à cobrança.</p>
                <p><strong>3.3 Faturação:</strong> A fatura será enviada por email após confirmação do pagamento.</p>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-white mb-4">4. Entrega</h2>
              <div className="text-gray-300 space-y-3">
                <p><strong>4.1 Prazos:</strong> Portugal Continental: 3-5 dias úteis. Ilhas e outros destinos: 7-10 dias úteis.</p>
                <p><strong>4.2 Custos:</strong> Os custos de envio são calculados no checkout conforme o destino.</p>
                <p><strong>4.3 Responsabilidade:</strong> Após a entrega, a responsabilidade pelos produtos é transferida para o cliente.</p>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-white mb-4">5. Devoluções e Reclamações</h2>
              <div className="text-gray-300 space-y-3">
                <p><strong>5.1 Política:</strong> Devido à natureza surpresa dos produtos, não aceitamos devoluções, exceto em caso de produtos danificados.</p>
                <p><strong>5.2 Produtos Danificados:</strong> Reporta produtos danificados em 48h após receção através do nosso apoio ao cliente.</p>
                <p><strong>5.3 Livro de Reclamações:</strong> Disponível online ou nas nossas instalações.</p>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-white mb-4">6. Assinaturas</h2>
              <div className="text-gray-300 space-y-3">
                <p><strong>6.1 Renovação:</strong> As assinaturas renovam automaticamente conforme a periodicidade escolhida.</p>
                <p><strong>6.2 Cancelamento:</strong> Podes cancelar a assinatura a qualquer momento através do teu perfil.</p>
                <p><strong>6.3 Pausar:</strong> É possível pausar temporariamente a assinatura por até 3 meses.</p>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-white mb-4">7. Proteção de Dados</h2>
              <div className="text-gray-300 space-y-3">
                <p><strong>7.1 RGPD:</strong> Cumprimos integralmente o Regulamento Geral de Proteção de Dados.</p>
                <p><strong>7.2 Finalidade:</strong> Os dados pessoais são utilizados apenas para processamento de encomendas e comunicação.</p>
                <p><strong>7.3 Direitos:</strong> Tens direito a aceder, retificar ou eliminar os teus dados pessoais.</p>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-white mb-4">8. Limitação de Responsabilidade</h2>
              <p className="text-gray-300">
                A nossa responsabilidade está limitada ao valor pago pelos produtos. Não nos responsabilizamos por danos indiretos ou lucros cessantes.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-white mb-4">9. Alterações aos Termos</h2>
              <p className="text-gray-300">
                Reservamo-nos o direito de alterar estes termos a qualquer momento. As alterações entram em vigor após publicação no website.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-white mb-4">10. Lei Aplicável</h2>
              <p className="text-gray-300">
                Estes termos são regidos pela lei portuguesa. Qualquer litígio será resolvido pelos tribunais competentes em Portugal.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-white mb-4">11. Contactos</h2>
              <div className="text-gray-300">
                <p><strong>Mystery Box Store</strong></p>
                <p>Email: legal@mysteryboxstore.pt</p>
                <p>Telefone: +351 123 456 789</p>
                <p>Morada: Rua das Mystery Boxes, 123, 1000-001 Lisboa</p>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
};

// Footer Component
const Footer = () => {
  const isMobile = useIsMobile();

  return (
    <footer className="bg-gradient-to-t from-black to-gray-900 text-white border-t border-purple-500/30">
      <div className="container mx-auto px-4 py-12">
        <div className={`grid ${isMobile ? 'grid-cols-1 gap-8' : 'md:grid-cols-4 gap-8'} mb-8`}>
          {/* Logo and Description */}
          <div className={`${isMobile ? 'text-center' : ''} md:col-span-1`}>
            <h3 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent mb-4">
              🎁 Mystery Box Store
            </h3>
            <p className="text-gray-400 text-sm leading-relaxed">
              Descobre o inesperado com as nossas mystery boxes temáticas. 
              Cada caixa é uma aventura única cheia de surpresas incríveis!
            </p>
          </div>

          {/* Quick Links */}
          <div className={`${isMobile ? 'text-center' : ''}`}>
            <h4 className="text-lg font-semibold mb-4 text-purple-300">🔗 Links Rápidos</h4>
            <ul className="space-y-2 text-sm">
              <li><Link to="/produtos" className="text-gray-400 hover:text-purple-300 transition-colors duration-300">📦 Produtos</Link></li>
              <li><Link to="/perfil" className="text-gray-400 hover:text-purple-300 transition-colors duration-300">👤 Meu Perfil</Link></li>
              <li><Link to="/carrinho" className="text-gray-400 hover:text-purple-300 transition-colors duration-300">🛒 Carrinho</Link></li>
            </ul>
          </div>

          {/* Support */}
          <div className={`${isMobile ? 'text-center' : ''}`}>
            <h4 className="text-lg font-semibold mb-4 text-purple-300">🛟 Apoio</h4>
            <ul className="space-y-2 text-sm">
              <li><Link to="/faq" className="text-gray-400 hover:text-purple-300 transition-colors duration-300">❓ FAQ</Link></li>
              <li><Link to="/termos" className="text-gray-400 hover:text-purple-300 transition-colors duration-300">📋 Termos e Condições</Link></li>
              <li><span className="text-gray-400">📧 edupodept@gmail.com</span></li>
              <li><span className="text-gray-400">📞 +351 913090641</span></li>
            </ul>
          </div>

          {/* Newsletter */}
          <div className={`${isMobile ? 'text-center' : ''}`}>
            <h4 className="text-lg font-semibold mb-4 text-purple-300">📬 Newsletter</h4>
            <p className="text-gray-400 text-sm mb-4">
              Recebe novidades e ofertas exclusivas!
            </p>
            <div className={`flex ${isMobile ? 'flex-col space-y-2' : 'space-x-2'}`}>
              <input
                type="email"
                placeholder="teu@email.com"
                className={`${isMobile ? 'w-full' : 'flex-1'} bg-gray-800 border border-purple-500/30 rounded-lg px-3 py-2 text-sm focus:border-purple-400 focus:outline-none`}
              />
              <button className={`${isMobile ? 'w-full' : ''} bg-gradient-to-r from-purple-600 to-pink-600 text-white px-4 py-2 rounded-lg text-sm hover:from-purple-700 hover:to-pink-700 transition-all duration-300`}>
                Subscrever
              </button>
            </div>
          </div>
        </div>

        {/* Social Media and Copyright */}
        <div className={`border-t border-purple-500/30 pt-6 ${isMobile ? 'text-center' : 'flex items-center justify-between'}`}>
          <div className={`${isMobile ? 'mb-4' : ''}`}>
            <p className="text-gray-400 text-sm">
              © 2025 Mystery Box Store. Todos os direitos reservados.
            </p>
          </div>
          
          <div className="flex items-center justify-center space-x-4">
            <span className="text-gray-400 text-sm">Segue-nos:</span>
            <div className="flex space-x-3">
              <a href="#" className="text-gray-400 hover:text-purple-300 transition-colors duration-300">📘</a>
              <a href="#" className="text-gray-400 hover:text-purple-300 transition-colors duration-300">📷</a>
              <a href="#" className="text-gray-400 hover:text-purple-300 transition-colors duration-300">🐦</a>
              <a href="#" className="text-gray-400 hover:text-purple-300 transition-colors duration-300">📺</a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};

// Lazy loading components for better performance
const LazyHome = lazy(() => Promise.resolve({ default: Home }));
const LazyProducts = lazy(() => Promise.resolve({ default: Products }));
const LazyProductDetail = lazy(() => Promise.resolve({ default: ProductDetail }));
const LazyCart = lazy(() => Promise.resolve({ default: Cart }));
const LazyCheckout = lazy(() => Promise.resolve({ default: Checkout }));
const LazyLogin = lazy(() => Promise.resolve({ default: Login }));
const LazyAdminDashboard = lazy(() => Promise.resolve({ default: AdminDashboard }));
const LazyAdminUsers = lazy(() => Promise.resolve({ default: AdminUsers }));
const LazyAdminOrders = lazy(() => Promise.resolve({ default: AdminOrders }));
const LazyAdminProducts = lazy(() => Promise.resolve({ default: AdminProducts }));
const LazyAdminCoupons = lazy(() => Promise.resolve({ default: AdminCoupons }));
const LazyAdminPromotions = lazy(() => Promise.resolve({ default: AdminPromotions }));
const LazyAdminCategories = lazy(() => Promise.resolve({ default: AdminCategories }));
const LazyAdminEmails = lazy(() => Promise.resolve({ default: AdminEmails }));
const LazyAdminSubscriptions = lazy(() => Promise.resolve({ default: AdminSubscriptions }));
const LazyAdminChatDashboard = lazy(() => Promise.resolve({ default: AdminChatDashboard }));
const LazyUserProfile = lazy(() => Promise.resolve({ default: UserProfile }));
const LazyFAQ = lazy(() => Promise.resolve({ default: FAQ }));
const LazyTermsAndConditions = lazy(() => Promise.resolve({ default: TermsAndConditions }));

const App = () => {
  const [showOrderDetails, setShowOrderDetails] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState(null);

  return (
    <DeviceProvider>
      <div className="App min-h-screen bg-gray-900">
        <Router>
          <Header />
          <Suspense fallback={
            <div className="flex items-center justify-center min-h-screen bg-gray-900">
              <div className="text-center">
                <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-purple-500 mx-auto mb-4"></div>
                <p className="text-white text-lg">Carregando...</p>
              </div>
            </div>
          }>
            <Routes>
              <Route path="/" element={<LazyHome />} />
              <Route path="/produtos" element={<LazyProducts />} />
              <Route path="/produto/:id" element={<LazyProductDetail />} />
              <Route path="/carrinho" element={<LazyCart />} />
              <Route path="/checkout" element={<LazyCheckout />} />
              <Route path="/success" element={<Success />} />
              <Route path="/login" element={<LazyLogin />} />
              <Route path="/admin" element={<LazyAdminDashboard />} />
              <Route path="/admin/users" element={<LazyAdminUsers />} />
              <Route path="/admin/orders" element={<LazyAdminOrders />} />
              <Route path="/admin/products" element={<LazyAdminProducts />} />
              <Route path="/admin/coupons" element={<LazyAdminCoupons />} />
              <Route path="/admin/promotions" element={<LazyAdminPromotions />} />
              <Route path="/admin/categories" element={<LazyAdminCategories />} />
              <Route path="/admin/emails" element={<LazyAdminEmails />} />
              <Route path="/admin/subscriptions" element={<LazyAdminSubscriptions />} />
              <Route path="/admin/chat" element={<LazyAdminChatDashboard />} />
              <Route path="/perfil" element={<LazyUserProfile />} />
              <Route path="/faq" element={<LazyFAQ />} />
              <Route path="/termos" element={<LazyTermsAndConditions />} />
            </Routes>
          </Suspense>
          <Footer />
          <LiveChatButton />

          {/* Order Details Modal */}
          {showOrderDetails && selectedOrder && (
            <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
              <div className="bg-gray-800 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto border border-purple-500/30">
                <div className="sticky top-0 bg-gray-800 border-b border-purple-500/30 p-6">
                  <div className="flex items-center justify-between">
                    <h3 className="text-2xl font-bold text-white">
                      📋 Detalhes do Pedido #{selectedOrder.id.slice(0, 8)}
                    </h3>
                    <button
                      onClick={() => setShowOrderDetails(false)}
                      className="text-gray-400 hover:text-white text-xl"
                    >
                      ✕
                    </button>
                  </div>
                </div>

                <div className="p-6 space-y-6">
                  {/* Order Info */}
                  <div className="grid md:grid-cols-2 gap-6">
                    <div className="bg-gray-700/50 rounded-lg p-4">
                      <h4 className="text-lg font-semibold text-white mb-3">Informações do Pedido</h4>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-400">Status Pagamento:</span>
                          <span className={`font-semibold ${
                            selectedOrder.payment_status === 'paid' ? 'text-green-400' :
                            selectedOrder.payment_status === 'pending' ? 'text-yellow-400' :
                            'text-red-400'
                          }`}>
                            {selectedOrder.payment_status}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Status Pedido:</span>
                          <span className="text-purple-400 font-semibold">
                            {selectedOrder.order_status}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Data:</span>
                          <span className="text-white">
                            {new Date(selectedOrder.created_at).toLocaleString('pt-PT')}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Método Pagamento:</span>
                          <span className="text-white">{selectedOrder.payment_method}</span>
                        </div>
                      </div>
                    </div>

                    <div className="bg-gray-700/50 rounded-lg p-4">
                      <h4 className="text-lg font-semibold text-white mb-3">Cliente</h4>
                      <div className="space-y-2 text-sm">
                        {selectedOrder.user_details ? (
                          <>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Nome:</span>
                              <span className="text-white">{selectedOrder.user_details.name}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Email:</span>
                              <span className="text-white">{selectedOrder.user_details.email}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Telefone:</span>
                              <span className="text-white">{selectedOrder.user_details.phone || 'N/A'}</span>
                            </div>
                          </>
                        ) : (
                          <span className="text-gray-400">Cliente Convidado</span>
                        )}
                        <div className="flex justify-between">
                          <span className="text-gray-400">Telefone Pedido:</span>
                          <span className="text-white">{selectedOrder.phone}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Shipping Info */}
                  <div className="bg-gray-700/50 rounded-lg p-4">
                    <h4 className="text-lg font-semibold text-white mb-3">Informações de Entrega</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Endereço:</span>
                        <span className="text-white">{selectedOrder.shipping_address}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Método de Envio:</span>
                        <span className="text-white">{selectedOrder.shipping_method}</span>
                      </div>
                      {selectedOrder.nif && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">NIF:</span>
                          <span className="text-white">{selectedOrder.nif}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Products */}
                  <div className="bg-gray-700/50 rounded-lg p-4">
                    <h4 className="text-lg font-semibold text-white mb-3">Produtos Comprados</h4>
                    <div className="space-y-4">
                      {selectedOrder.detailed_items?.map((item, index) => {
                        const product = item.product;
                        const price = item.subscription_type 
                          ? product.subscription_prices[item.subscription_type] 
                          : product.price;
                        const totalPrice = price * item.quantity;

                        return (
                          <div key={index} className="flex items-center space-x-4 bg-gray-600/30 rounded-lg p-3">
                            <img 
                              src={product.image_url} 
                              alt={product.name}
                              className="w-16 h-16 object-cover rounded-lg"
                            />
                            <div className="flex-1">
                              <h5 className="font-semibold text-white">{product.name}</h5>
                              <p className="text-sm text-gray-400">{product.description}</p>
                              {item.subscription_type && (
                                <p className="text-sm text-purple-400">
                                  📅 Assinatura: {item.subscription_type.replace('_', ' ')}
                                </p>
                              )}
                              <div className="flex items-center justify-between mt-2">
                                <span className="text-sm text-gray-400">
                                  Quantidade: {item.quantity} × €{price.toFixed(2)}
                                </span>
                                <span className="font-semibold text-purple-400">
                                  €{totalPrice.toFixed(2)}
                                </span>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Order Summary */}
                  <div className="bg-gray-700/50 rounded-lg p-4">
                    <h4 className="text-lg font-semibold text-white mb-3">Resumo Financeiro</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between text-gray-300">
                        <span>Subtotal:</span>
                        <span>€{selectedOrder.subtotal?.toFixed(2)}</span>
                      </div>
                      {selectedOrder.discount_amount > 0 && (
                        <div className="flex justify-between text-green-400">
                          <span>Desconto ({selectedOrder.coupon_code}):</span>
                          <span>-€{selectedOrder.discount_amount?.toFixed(2)}</span>
                        </div>
                      )}
                      <div className="flex justify-between text-gray-300">
                        <span>IVA:</span>
                        <span>€{selectedOrder.vat_amount?.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between text-gray-300">
                        <span>Envio:</span>
                        <span>€{selectedOrder.shipping_cost?.toFixed(2)}</span>
                      </div>
                      <hr className="border-gray-600" />
                      <div className="flex justify-between text-xl font-bold text-purple-400">
                        <span>Total:</span>
                        <span>€{selectedOrder.total_amount?.toFixed(2)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </Router>
      </div>
    </DeviceProvider>
  );
};

// Admin Subscriptions Management Component
const AdminSubscriptions = () => {
  const [subscriptions, setSubscriptions] = useState([]);
  const [deliveries, setDeliveries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('subscriptions');
  const [processing, setProcessing] = useState(false);
  const { user } = useDeviceContext();
  const isMobile = useIsMobile();

  useEffect(() => {
    if (user?.is_admin) {
      loadSubscriptions();
      loadDeliveries();
    }
  }, [user]);

  const loadSubscriptions = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/admin/subscriptions`);
      setSubscriptions(response.data);
    } catch (error) {
      console.error('Error loading subscriptions:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadDeliveries = async () => {
    try {
      const response = await axios.get(`${API}/admin/subscription-deliveries`);
      setDeliveries(response.data);
    } catch (error) {
      console.error('Error loading deliveries:', error);
    }
  };

  const handleUpdateStatus = async (subscriptionId, status) => {
    try {
      await axios.put(`${API}/admin/subscriptions/${subscriptionId}/status?status=${status}`);
      alert('Status da assinatura atualizado com sucesso!');
      loadSubscriptions();
    } catch (error) {
      console.error('Error updating subscription status:', error);
      alert('Erro ao atualizar status: ' + (error.response?.data?.detail || 'Erro desconhecido'));
    }
  };

  const handleProcessDeliveries = async () => {
    if (!window.confirm('Processar entregas de assinaturas agendadas para hoje?')) {
      return;
    }

    try {
      setProcessing(true);
      const response = await axios.post(`${API}/admin/subscriptions/process-deliveries`);
      alert(response.data.message);
      loadSubscriptions();
      loadDeliveries();
    } catch (error) {
      console.error('Error processing deliveries:', error);
      alert('Erro ao processar entregas: ' + (error.response?.data?.detail || 'Erro desconhecido'));
    } finally {
      setProcessing(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'text-green-400';
      case 'paused': return 'text-yellow-400';
      case 'cancelled': return 'text-red-400';
      case 'completed': return 'text-blue-400';
      default: return 'text-gray-400';
    }
  };

  if (!user?.is_admin) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black flex items-center justify-center">
        <div className="text-center text-white">
          <div className="text-8xl mb-4">🚫</div>
          <h1 className="text-4xl font-bold mb-4">Acesso Negado</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-900 to-black">
      <div className="container mx-auto px-4 py-12">
        <div className="flex items-center mb-8">
          <Link to="/admin" className="text-purple-400 hover:text-purple-300 mr-4">
            ← Voltar ao Admin
          </Link>
          <h1 className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold text-white`}>
            📅 Gestão de Assinaturas
          </h1>
        </div>

        {/* Action Buttons */}
        <div className="mb-8 flex gap-4">
          <button
            onClick={handleProcessDeliveries}
            disabled={processing}
            className="bg-gradient-to-r from-green-600 to-green-700 text-white px-6 py-3 rounded-lg hover:from-green-700 hover:to-green-800 transition-all duration-300 disabled:opacity-50"
          >
            {processing ? (
              <span className="flex items-center">
                <div className="animate-spin mr-2">🔮</div>
                Processando...
              </span>
            ) : (
              '🚀 Processar Entregas Pendentes'
            )}
          </button>
        </div>

        {/* Tabs */}
        <div className="mb-8">
          <div className="flex space-x-1 bg-gray-800/50 rounded-lg p-1">
            <button
              onClick={() => setActiveTab('subscriptions')}
              className={`flex-1 py-3 px-4 rounded-lg transition-all duration-300 ${
                activeTab === 'subscriptions'
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              📅 Assinaturas Ativas
            </button>
            <button
              onClick={() => setActiveTab('deliveries')}
              className={`flex-1 py-3 px-4 rounded-lg transition-all duration-300 ${
                activeTab === 'deliveries'
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              📦 Histórico de Entregas
            </button>
          </div>
        </div>

        {/* Subscriptions Tab */}
        {activeTab === 'subscriptions' && (
          <div className="bg-gray-800/50 rounded-2xl border border-purple-500/30 overflow-hidden">
            <div className="p-6 border-b border-purple-500/30">
              <h3 className="text-xl font-bold text-white">📋 Assinaturas Ativas</h3>
            </div>
            
            {loading ? (
              <div className="text-center text-white p-12">
                <div className="animate-spin text-6xl mb-4">🔮</div>
                <p>Carregando assinaturas...</p>
              </div>
            ) : subscriptions.length === 0 ? (
              <div className="text-center text-gray-400 p-12">
                <div className="text-6xl mb-4">📅</div>
                <p>Nenhuma assinatura encontrada</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-white">
                  <thead className="bg-purple-900/50">
                    <tr>
                      <th className="text-left p-4">Cliente</th>
                      <th className="text-left p-4">Produto</th>
                      <th className="text-left p-4">Tipo</th>
                      <th className="text-left p-4">Progresso</th>
                      <th className="text-left p-4">Próxima Entrega</th>
                      <th className="text-left p-4">Status</th>
                      <th className="text-left p-4">Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {subscriptions.map((subscription) => (
                      <tr key={subscription.id} className="border-b border-gray-700 hover:bg-gray-700/30">
                        <td className="p-4">
                          <div>
                            <div className="font-semibold">{subscription.user_name}</div>
                            <div className="text-sm text-gray-400">{subscription.user_email}</div>
                          </div>
                        </td>
                        <td className="p-4">{subscription.product_name}</td>
                        <td className="p-4">
                          <span className="px-2 py-1 bg-purple-900/50 rounded-full text-sm">
                            {subscription.subscription_type.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="p-4">
                          <div className="flex items-center space-x-2">
                            <span className="font-bold text-purple-400">{subscription.progress_text}</span>
                            <div className="w-20 bg-gray-600 rounded-full h-2">
                              <div 
                                className="bg-purple-500 h-2 rounded-full" 
                                style={{
                                  width: `${(subscription.current_cycle / subscription.total_cycles) * 100}%`
                                }}
                              ></div>
                            </div>
                          </div>
                        </td>
                        <td className="p-4">
                          <span className="text-sm">
                            {new Date(subscription.next_delivery_date).toLocaleDateString('pt-PT')}
                          </span>
                        </td>
                        <td className="p-4">
                          <span className={`font-semibold ${getStatusColor(subscription.status)}`}>
                            {subscription.status}
                          </span>
                        </td>
                        <td className="p-4">
                          <div className="flex space-x-2">
                            {subscription.status === 'active' && (
                              <button
                                onClick={() => handleUpdateStatus(subscription.id, 'paused')}
                                className="bg-yellow-600 hover:bg-yellow-700 text-white px-3 py-1 rounded text-sm transition-colors"
                              >
                                ⏸️ Pausar
                              </button>
                            )}
                            {subscription.status === 'paused' && (
                              <button
                                onClick={() => handleUpdateStatus(subscription.id, 'active')}
                                className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm transition-colors"
                              >
                                ▶️ Retomar
                              </button>
                            )}
                            {['active', 'paused'].includes(subscription.status) && (
                              <button
                                onClick={() => handleUpdateStatus(subscription.id, 'cancelled')}
                                className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm transition-colors"
                              >
                                ❌ Cancelar
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Deliveries Tab */}
        {activeTab === 'deliveries' && (
          <div className="bg-gray-800/50 rounded-2xl border border-purple-500/30 overflow-hidden">
            <div className="p-6 border-b border-purple-500/30">
              <h3 className="text-xl font-bold text-white">📦 Histórico de Entregas</h3>
            </div>
            
            {deliveries.length === 0 ? (
              <div className="text-center text-gray-400 p-12">
                <div className="text-6xl mb-4">📦</div>
                <p>Nenhuma entrega encontrada</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-white">
                  <thead className="bg-purple-900/50">
                    <tr>
                      <th className="text-left p-4">Data de Entrega</th>
                      <th className="text-left p-4">Cliente</th>
                      <th className="text-left p-4">Produto</th>
                      <th className="text-left p-4">Ciclo</th>
                      <th className="text-left p-4">Status</th>
                      <th className="text-left p-4">Pedido</th>
                    </tr>
                  </thead>
                  <tbody>
                    {deliveries.map((delivery) => (
                      <tr key={delivery.id} className="border-b border-gray-700 hover:bg-gray-700/30">
                        <td className="p-4">
                          {new Date(delivery.delivery_date).toLocaleDateString('pt-PT')}
                        </td>
                        <td className="p-4">
                          {delivery.subscription_info?.user_name || 'Cliente Desconhecido'}
                        </td>
                        <td className="p-4">
                          {delivery.subscription_info?.product_name || 'Produto Desconhecido'}
                        </td>
                        <td className="p-4">
                          <span className="px-2 py-1 bg-blue-900/50 rounded-full text-sm">
                            Ciclo {delivery.cycle_number}
                          </span>
                        </td>
                        <td className="p-4">
                          <span className={`font-semibold ${getStatusColor(delivery.status)}`}>
                            {delivery.status}
                          </span>
                        </td>
                        <td className="p-4">
                          <span className="text-sm text-gray-400">
                            #{delivery.order_id?.slice(0, 8)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default App;