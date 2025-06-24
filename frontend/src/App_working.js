import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';
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

const Products = () => {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('');
  const { addToCart } = useDeviceContext();
  const isMobile = useIsMobile();

  useEffect(() => {
    const loadData = async () => {
      try {
        const [productsRes, categoriesRes] = await Promise.all([
          axios.get(`${API}/products${selectedCategory ? `?category=${selectedCategory}` : ''}`),
          axios.get(`${API}/categories`)
        ]);
        setProducts(productsRes.data);
        setCategories(categoriesRes.data);
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
};

const App = () => {
  return (
    <DeviceProvider>
      <div className="App min-h-screen bg-gray-900">
        <BrowserRouter>
          <Header />
          <Routes>
            <Route path="/" element={<div>Home</div>} />
            <Route path="/produtos" element={<Products />} />
            <Route path="/produto/:id" element={<div>Product Detail</div>} />
            <Route path="/carrinho" element={<div>Cart</div>} />
            <Route path="/login" element={<div>Login</div>} />
            <Route path="/admin" element={<div>Admin</div>} />
            <Route path="/perfil" element={<div>Profile</div>} />
          </Routes>
        </BrowserRouter>
      </div>
    </DeviceProvider>
  );
};

export default App;