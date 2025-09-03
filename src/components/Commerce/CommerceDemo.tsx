import React, { useState, useEffect } from 'react';
import { 
  ShoppingCart, 
  Store, 
  Package, 
  CreditCard, 
  Truck,
  Search,
  Plus,
  Star,
  MapPin,
  Clock,
  DollarSign
} from 'lucide-react';
import { Product, Seller, Order, OrderItem, Address } from '../../types';
import { api } from '../../services/api';

export function CommerceDemo() {
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [cart, setCart] = useState<Array<{ product: Product; quantity: number }>>([]);
  const [selectedSeller, setSelectedSeller] = useState<string | null>(null);
  const [currentOrder, setCurrentOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      
      // Load sellers and products
      const [sellersResponse, productsResponse] = await Promise.all([
        api.getSellers(),
        api.getProducts()
      ]);
      
      setSellers(sellersResponse.sellers || []);
      setProducts(productsResponse.products || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      loadInitialData();
      return;
    }

    try {
      setLoading(true);
      const response = await api.searchProducts(searchQuery);
      setProducts(response.products || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const addToCart = (product: Product) => {
    setCart(prev => {
      const existing = prev.find(item => item.product.id === product.id);
      if (existing) {
        return prev.map(item =>
          item.product.id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        );
      }
      return [...prev, { product, quantity: 1 }];
    });
  };

  const removeFromCart = (productId: string) => {
    setCart(prev => prev.filter(item => item.product.id !== productId));
  };

  const updateCartQuantity = (productId: string, quantity: number) => {
    if (quantity <= 0) {
      removeFromCart(productId);
      return;
    }
    
    setCart(prev =>
      prev.map(item =>
        item.product.id === productId
          ? { ...item, quantity }
          : item
      )
    );
  };

  const calculateCartTotal = () => {
    return cart.reduce((total, item) => total + (item.product.price * item.quantity), 0);
  };

  const handleCheckout = async () => {
    if (cart.length === 0) return;

    // Group cart items by seller
    const sellerGroups = cart.reduce((groups, item) => {
      const sellerId = item.product.seller_id;
      if (!groups[sellerId]) {
        groups[sellerId] = [];
      }
      groups[sellerId].push(item);
      return groups;
    }, {} as Record<string, typeof cart>);

    try {
      setLoading(true);
      
      // For demo, create order with first seller group
      const firstSellerId = Object.keys(sellerGroups)[0];
      const firstSellerItems = sellerGroups[firstSellerId];
      
      const orderItems: OrderItem[] = firstSellerItems.map(item => ({
        product_id: item.product.id,
        title: item.product.title,
        quantity: item.quantity,
        unit_price: item.product.price,
        currency: item.product.currency,
        weight_kg: item.product.weight_kg
      }));

      const dropoffAddress: Address = {
        name: 'Demo Customer',
        phone: '+1-555-0123',
        address: '999 Market St, San Francisco, CA',
        latitude: 37.782,
        longitude: -122.41
      };

      // Get first product's fulfillment origin for pickup
      const firstProduct = firstSellerItems[0].product;
      const pickupLocation = firstProduct.fulfillment_origin || {
        latitude: 37.7749,
        longitude: -122.4194
      };

      const orderData = {
        seller_id: firstSellerId,
        items: orderItems,
        dropoff: dropoffAddress,
        buyer_did_identifier: 'demo_buyer_123',
        // Movement request fields
        service_type: 'delivery',
        pickup_location: {
          latitude: pickupLocation.latitude,
          longitude: pickupLocation.longitude
        },
        dropoff_location: {
          latitude: dropoffAddress.latitude,
          longitude: dropoffAddress.longitude
        },
        priority: 'normal'
      };

      const response = await api.createOrder(orderData);
      setCurrentOrder(response.order);
      
      // Clear cart
      setCart([]);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Checkout failed');
    } finally {
      setLoading(false);
    }
  };

  const filteredProducts = selectedSeller 
    ? products.filter(p => p.seller_id === selectedSeller)
    : products;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900 mb-4">
          Decentralized Commerce Demo
        </h2>
        <p className="text-lg text-gray-600 max-w-3xl mx-auto">
          Shop across multiple sellers with unified checkout and delivery optimization.
          Experience blockchain escrow and intelligent delivery routing.
        </p>
      </div>

      {/* Search and Filters */}
      <div className="card">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search products..."
                className="input-field pl-10"
              />
            </div>
          </div>
          
          <button
            onClick={handleSearch}
            className="btn-primary flex items-center space-x-2"
          >
            <Search className="w-4 h-4" />
            <span>Search</span>
          </button>
        </div>

        {/* Seller Filter */}
        {sellers.length > 0 && (
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filter by Seller
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setSelectedSeller(null)}
                className={`px-3 py-1 rounded-full text-sm transition-colors ${
                  !selectedSeller 
                    ? 'bg-primary-100 text-primary-700' 
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                All Sellers
              </button>
              {sellers.map((seller) => (
                <button
                  key={seller.id}
                  onClick={() => setSelectedSeller(seller.id)}
                  className={`px-3 py-1 rounded-full text-sm transition-colors ${
                    selectedSeller === seller.id 
                      ? 'bg-primary-100 text-primary-700' 
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {seller.name}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Products */}
        <div className="lg:col-span-2 space-y-6">
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="card animate-pulse">
                  <div className="h-32 bg-gray-200 rounded mb-4"></div>
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                </div>
              ))}
            </div>
          ) : filteredProducts.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {filteredProducts.map((product) => {
                const seller = sellers.find(s => s.id === product.seller_id);
                const inCart = cart.find(item => item.product.id === product.id);
                
                return (
                  <div key={product.id} className="card hover:shadow-md transition-shadow">
                    {/* Product Image */}
                    <div className="h-32 bg-gradient-to-br from-gray-100 to-gray-200 rounded-lg mb-4 flex items-center justify-center">
                      <Package className="w-12 h-12 text-gray-400" />
                    </div>
                    
                    {/* Product Info */}
                    <div className="space-y-3">
                      <div>
                        <h3 className="font-semibold text-gray-900">{product.title}</h3>
                        {product.description && (
                          <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                            {product.description}
                          </p>
                        )}
                      </div>
                      
                      {/* Seller Info */}
                      {seller && (
                        <div className="flex items-center space-x-2 text-sm">
                          <Store className="w-3 h-3 text-gray-400" />
                          <span className="text-gray-600">{seller.name}</span>
                          {seller.reputation_score > 0 && (
                            <div className="flex items-center space-x-1">
                              <Star className="w-3 h-3 text-yellow-500 fill-current" />
                              <span className="text-gray-500">{seller.reputation_score.toFixed(1)}</span>
                            </div>
                          )}
                        </div>
                      )}
                      
                      {/* Categories */}
                      {product.categories.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {product.categories.slice(0, 3).map((category) => (
                            <span
                              key={category}
                              className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full"
                            >
                              {category}
                            </span>
                          ))}
                        </div>
                      )}
                      
                      {/* Price and Actions */}
                      <div className="flex items-center justify-between pt-2">
                        <div>
                          <span className="text-2xl font-bold text-gray-900">
                            ${product.price.toFixed(2)}
                          </span>
                          <span className="text-sm text-gray-500 ml-1">{product.currency}</span>
                        </div>
                        
                        {inCart ? (
                          <div className="flex items-center space-x-2">
                            <button
                              onClick={() => updateCartQuantity(product.id, inCart.quantity - 1)}
                              className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-600 hover:bg-gray-300"
                            >
                              -
                            </button>
                            <span className="w-8 text-center font-medium">{inCart.quantity}</span>
                            <button
                              onClick={() => updateCartQuantity(product.id, inCart.quantity + 1)}
                              className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center text-white hover:bg-primary-700"
                            >
                              +
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => addToCart(product)}
                            className="btn-primary flex items-center space-x-2"
                          >
                            <Plus className="w-4 h-4" />
                            <span>Add</span>
                          </button>
                        )}
                      </div>
                      
                      {/* Inventory */}
                      <div className="text-xs text-gray-500">
                        {product.inventory > 0 ? (
                          `${product.inventory} in stock`
                        ) : (
                          <span className="text-red-600">Out of stock</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="card text-center py-12">
              <Package className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Products Found</h3>
              <p className="text-gray-600">
                {searchQuery ? 'Try a different search term' : 'No products available'}
              </p>
            </div>
          )}
        </div>

        {/* Shopping Cart */}
        <div className="space-y-6">
          <div className="card sticky top-24">
            <div className="flex items-center space-x-2 mb-4">
              <ShoppingCart className="w-5 h-5 text-gray-600" />
              <h3 className="text-lg font-semibold text-gray-900">
                Shopping Cart ({cart.length})
              </h3>
            </div>

            {cart.length === 0 ? (
              <div className="text-center py-8">
                <ShoppingCart className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-600">Your cart is empty</p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Cart Items */}
                <div className="space-y-3 max-h-64 overflow-y-auto custom-scrollbar">
                  {cart.map((item) => (
                    <div key={item.product.id} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-900 text-sm">{item.product.title}</h4>
                        <p className="text-xs text-gray-600">
                          ${item.product.price.toFixed(2)} each
                        </p>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => updateCartQuantity(item.product.id, item.quantity - 1)}
                          className="w-6 h-6 rounded-full bg-gray-200 flex items-center justify-center text-gray-600 hover:bg-gray-300 text-sm"
                        >
                          -
                        </button>
                        <span className="w-6 text-center text-sm font-medium">{item.quantity}</span>
                        <button
                          onClick={() => updateCartQuantity(item.product.id, item.quantity + 1)}
                          className="w-6 h-6 rounded-full bg-primary-600 flex items-center justify-center text-white hover:bg-primary-700 text-sm"
                        >
                          +
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Cart Total */}
                <div className="border-t border-gray-200 pt-4">
                  <div className="flex justify-between items-center mb-4">
                    <span className="font-medium text-gray-900">Total:</span>
                    <span className="text-xl font-bold text-gray-900">
                      ${calculateCartTotal().toFixed(2)}
                    </span>
                  </div>

                  <button
                    onClick={handleCheckout}
                    disabled={loading}
                    className="w-full btn-primary flex items-center justify-center space-x-2"
                  >
                    {loading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        <span>Processing...</span>
                      </>
                    ) : (
                      <>
                        <CreditCard className="w-4 h-4" />
                        <span>Checkout with Escrow</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Demo Features */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Demo Features</h3>
            <div className="space-y-3 text-sm">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span>Multi-seller optimization</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                <span>Flow blockchain escrow</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                <span>Intelligent delivery routing</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-orange-500 rounded-full"></div>
                <span>Real-time order tracking</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="card border-red-200 bg-red-50">
          <div className="flex items-center space-x-2 text-red-700">
            <Package className="w-5 h-5" />
            <span className="font-medium">Error</span>
          </div>
          <p className="text-red-600 mt-2">{error}</p>
        </div>
      )}

      {/* Current Order Display */}
      {currentOrder && (
        <div className="card border-green-200 bg-green-50">
          <div className="flex items-center space-x-2 text-green-700 mb-4">
            <Package className="w-5 h-5" />
            <span className="font-medium">Order Created Successfully!</span>
          </div>
          
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Order ID:</span>
                <span className="ml-2 font-mono text-gray-900">{currentOrder.id}</span>
              </div>
              <div>
                <span className="text-gray-600">Status:</span>
                <span className="ml-2 font-medium text-green-700 capitalize">{currentOrder.status}</span>
              </div>
              <div>
                <span className="text-gray-600">Total:</span>
                <span className="ml-2 font-bold text-gray-900">${currentOrder.total.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-gray-600">Items:</span>
                <span className="ml-2 text-gray-900">{currentOrder.items.length}</span>
              </div>
            </div>
            
            <div className="pt-3 border-t border-green-200">
              <p className="text-sm text-green-700">
                ✅ Escrow created and funded on Flow blockchain
              </p>
              <p className="text-sm text-green-700">
                🚚 Delivery quotes requested from all providers
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}