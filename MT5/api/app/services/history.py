import MetaTrader5 as mt5
from typing import Optional, List, Dict
from datetime import datetime
from .connector import mt5_connector

class HistoryService:
    def get_history_deals(self, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None, position: Optional[int] = None) -> Optional[List[Dict]]:
        mt5_connector.initialize()
        date_from = from_date if from_date else datetime(1970, 1, 1)
        date_to = to_date if to_date else datetime.now()
        deals = mt5.history_deals_get(date_from, date_to, position=position) if position else mt5.history_deals_get(date_from, date_to)
        if deals is None: return None
        return [d._asdict() for d in deals]

    def get_history_orders(self, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None, ticket: Optional[int] = None) -> Optional[List[Dict]]:
        mt5_connector.initialize()
        if ticket:
            orders = mt5.history_orders_get(ticket=ticket)
        else:
            date_from = from_date if from_date else datetime(1970, 1, 1)
            date_to = to_date if to_date else datetime.now()
            orders = mt5.history_orders_get(date_from, date_to)
        if orders is None: return None
        return [o._asdict() for o in orders]

history_service = HistoryService()
