from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from app.db.database import get_session
from app.models.trade import Trade, TradeBase
from app.services.mt5_service import mt5_service
from app.models.trading import MarketOrderRequest, ModifySLTPRequest
from app.utils.exceptions import MT5SymbolNotFoundError, MT5OrderError
from app.db import crud
from app.utils import helpers
import MetaTrader5 as mt5

router = APIRouter(prefix="/trading", tags=["Trading"])


@router.get("/", response_model=List[Trade])
def get_trades(
    symbol: Optional[str] = None,
    trade_type: Optional[str] = None,
    is_open: Optional[bool] = None,
    session: Session = Depends(get_session)
):
    statement = select(Trade)
    if symbol:
        statement = statement.where(Trade.symbol == symbol.upper())
    if trade_type:
        statement = statement.where(Trade.type == trade_type.upper())
    if is_open is True:
        statement = statement.where(Trade.close_time == None)
    elif is_open is False:
        statement = statement.where(Trade.close_time != None)
    return session.exec(statement).all()


# @router.post("/trades", response_model=Trade, status_code=status.HTTP_201_CREATED)
# def create_trade(trade_data: TradeBase, session: Session = Depends(get_session)):
#     trade = Trade.from_orm(trade_data)
#     session.add(trade)
#     session.commit()
#     session.refresh(trade)
#     return trade


# @router.post("/order", status_code=status.HTTP_201_CREATED)
# def send_order(
#     request: MarketOrderRequest,
#     session: Session = Depends(get_session)
# ):
#     result = mt5_service.send_market_order(
#         symbol=request.symbol,
#         volume=request.volume,
#         order_type=request.order_type,
#         sl=request.sl,
#         tp=request.tp,
#         deviation=request.deviation,
#         comment=request.comment,
#         magic=request.magic,
#         type_filling=request.type_filling
#     )
#     info = mt5_service.get_symbol_info(request.symbol)
#     contract_size = info.get('trade_contract_size', 100000)
#     leverage = 500
#     order_size_usd = request.volume * contract_size * result.price
#     capital_used = order_size_usd / leverage
#     commission = helpers.calculate_commission(order_size_usd, request.symbol)
#     trade = crud.create_trade(
#         session=session,
#         order_result=result._asdict(),
#         symbol=request.symbol,
#         capital=capital_used,
#         position_size_usd=order_size_usd,
#         leverage=leverage,
#         commission=commission,
#         trade_type=request.order_type,
#         broker="MT5",
#         market_type="OTHER",
#         strategy="MANUAL",
#         timeframe="M1",
#         volume=request.volume,
#         sl=request.sl,
#         tp=request.tp
#     )
#     return {"success": True, "trade": trade}


# @router.post("/modify-sl-tp")
# def modify_sl_tp(
#     request: ModifySLTPRequest,
#     trade_id: int,
#     session: Session = Depends(get_session)
# ):
#     trade = session.get(Trade, trade_id)
#     if not trade:
#         raise HTTPException(status_code=404, detail="Trade not found in database")

#     ticket = int(trade.transaction_broker_id)
#     result = mt5_service.modify_sl_tp(ticket, request.sl, request.tp)
#     if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
#         raise MT5OrderError(
#             f"Modify SL/TP failed: {getattr(result, 'comment', 'Unknown error')}",
#             code=getattr(result, 'retcode', None)
#         )

#     mutation = crud.mutate_trade(
#         session=session,
#         trade_id=trade.id,
#         mutation_price=mt5_service.get_symbol_info(trade.symbol).get('bid', 0.0),
#         new_sl=request.sl,
#         new_tp=request.tp
#     )
#     return {"success": True, "mutation": mutation}


@router.get("/order_check/{symbol}")
def check_order(symbol: str):
    mt5_service.initialize()
    info = mt5.symbol_info(symbol)
    if not info:
        raise MT5SymbolNotFoundError(f"Symbol '{symbol}' not found")
    return info._asdict()
