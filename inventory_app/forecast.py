import pandas as pd
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from django.utils import timezone
from .models import Sale, InventoryItem, SalesForecast
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

class SalesForecastService:
    """
    AI-powered sales forecasting service using historical data
    """
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.model = LinearRegression()
    
    def prepare_historical_data(self, item_id, days_back=90):
        """
        Prepare historical sales data for the specified item
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        # Get daily sales data
        sales_data = Sale.objects.filter(
            item_id=item_id,
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date
        ).values('timestamp__date').annotate(
            daily_quantity=Sum('quantity'),
            daily_revenue=Sum('total_price'),
            sales_count=Count('id')
        ).order_by('timestamp__date')
        
        if not sales_data:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(sales_data)
        df['date'] = pd.to_datetime(df['timestamp__date'])
        df.set_index('date', inplace=True)
        
        # Fill missing dates with zero sales
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        df = df.reindex(date_range, fill_value=0)
        
        return df
    
    def create_features(self, df):
        """
        Create features for machine learning model
        """
        df = df.copy()
        
        # Time-based features
        df['day_of_week'] = df.index.dayofweek
        df['day_of_month'] = df.index.day
        df['month'] = df.index.month
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        
        # Rolling averages
        df['qty_7day_avg'] = df['daily_quantity'].rolling(window=7, min_periods=1).mean()
        df['qty_14day_avg'] = df['daily_quantity'].rolling(window=14, min_periods=1).mean()
        df['qty_30day_avg'] = df['daily_quantity'].rolling(window=30, min_periods=1).mean()
        
        # Lag features
        df['qty_lag_1'] = df['daily_quantity'].shift(1)
        df['qty_lag_7'] = df['daily_quantity'].shift(7)
        
        # Trend features
        df['days_since_start'] = range(len(df))
        
        return df
    
    def train_model(self, item_id, days_back=90):
        """
        Train the forecasting model for a specific item
        """
        df = self.prepare_historical_data(item_id, days_back)
        
        if df is None or len(df) < 14:
            return False, "Insufficient historical data"
        
        # Create features
        df = self.create_features(df)
        
        # Define feature columns
        feature_columns = [
            'day_of_week', 'day_of_month', 'month', 'is_weekend',
            'qty_7day_avg', 'qty_14day_avg', 'qty_30day_avg',
            'qty_lag_1', 'qty_lag_7', 'days_since_start'
        ]
        
        # Remove rows with NaN values
        df_clean = df.dropna()
        
        if len(df_clean) < 7:
            return False, "Insufficient clean data after feature engineering"
        
        # Prepare training data
        X = df_clean[feature_columns]
        y = df_clean['daily_quantity']
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled, y)
        
        return True, "Model trained successfully"
    
    def predict_sales(self, item_id, forecast_days=30):
        """
        Predict sales for the next forecast_days
        """
        df = self.prepare_historical_data(item_id)
        
        if df is None:
            return None, "No historical data available"
        
        # Train model
        success, message = self.train_model(item_id)
        if not success:
            return None, message
        
        # Create features for historical data
        df = self.create_features(df)
        
        predictions = []
        current_date = timezone.now().date() + timedelta(days=1)
        
        # Get last known values for lag features
        last_values = df.tail(7)['daily_quantity'].values
        
        for i in range(forecast_days):
            pred_date = current_date + timedelta(days=i)
            
            # Create features for prediction date
            features = {
                'day_of_week': pred_date.weekday(),
                'day_of_month': pred_date.day,
                'month': pred_date.month,
                'is_weekend': 1 if pred_date.weekday() >= 5 else 0,
                'qty_7day_avg': np.mean(last_values[-7:]) if len(last_values) >= 7 else 0,
                'qty_14day_avg': np.mean(last_values[-14:]) if len(last_values) >= 14 else 0,
                'qty_30day_avg': np.mean(last_values[-30:]) if len(last_values) >= 30 else 0,
                'qty_lag_1': last_values[-1] if len(last_values) > 0 else 0,
                'qty_lag_7': last_values[-7] if len(last_values) >= 7 else 0,
                'days_since_start': len(df) + i + 1
            }
            
            # Convert to array and scale
            feature_array = np.array([[features[col] for col in [
                'day_of_week', 'day_of_month', 'month', 'is_weekend',
                'qty_7day_avg', 'qty_14day_avg', 'qty_30day_avg',
                'qty_lag_1', 'qty_lag_7', 'days_since_start'
            ]]])
            
            feature_scaled = self.scaler.transform(feature_array)
            
            # Make prediction
            predicted_qty = max(0, int(self.model.predict(feature_scaled)[0]))
            
            predictions.append({
                'date': pred_date,
                'predicted_quantity': predicted_qty
            })
            
            # Update last_values for next iteration
            last_values = np.append(last_values, predicted_qty)
        
        return predictions, "Predictions generated successfully"
    
    def generate_forecast_for_item(self, item_id, forecast_days=30):
        """
        Generate and save forecast for a specific item
        """
        try:
            item = InventoryItem.objects.get(id=item_id)
        except InventoryItem.DoesNotExist:
            return False, "Item not found"
        
        predictions, message = self.predict_sales(item_id, forecast_days)
        
        if predictions is None:
            return False, message
        
        # Save predictions to database
        saved_forecasts = []
        for pred in predictions:
            forecast, created = SalesForecast.objects.update_or_create(
                item=item,
                forecast_date=pred['date'],
                defaults={'predicted_quantity': pred['predicted_quantity']}
            )
            saved_forecasts.append(forecast)
        
        return True, f"Generated {len(saved_forecasts)} forecasts for {item.name}"
    
    def generate_forecasts_for_all_items(self, forecast_days=30, min_sales_threshold=5):
        """
        Generate forecasts for all items with sufficient sales history
        """
        # Get items with recent sales
        recent_sales = Sale.objects.filter(
            timestamp__gte=timezone.now() - timedelta(days=30)
        ).values('item_id').annotate(
            total_sales=Count('id')
        ).filter(total_sales__gte=min_sales_threshold)
        
        results = []
        for sale_data in recent_sales:
            item_id = sale_data['item_id']
            success, message = self.generate_forecast_for_item(item_id, forecast_days)
            results.append({
                'item_id': item_id,
                'success': success,
                'message': message
            })
        
        return results