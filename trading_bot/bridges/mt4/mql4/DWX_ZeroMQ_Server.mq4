//+------------------------------------------------------------------+
//|                                          DWX_ZeroMQ_Server.mq4    |
//|                                 Copyright 2022, Lingonberry Trade |
//|                                                                   |
//+------------------------------------------------------------------+
#property copyright "Copyright 2022, Lingonberry Trade"
#property link      "https://github.com/yegor-stuba/Lingonberry-Trade"
#property version   "1.0"
#property strict

// ZeroMQ includes
#include <Zmq/Zmq.mqh>

// Globals
extern string PROJECT_NAME = "DWX_ZeroMQ_MT4_Server";
extern string ZEROMQ_PROTOCOL = "tcp";
extern string HOSTNAME = "*";
extern int PUSH_PORT = 5556;
extern int PULL_PORT = 5555;
extern int PUB_PORT = 5557;
extern int MILLISECOND_TIMER = 1;  // 1 millisecond

// ZeroMQ Context
Context context(PROJECT_NAME);

// ZeroMQ Publisher (Server side)
Socket publisher(context, ZMQ_PUB);

// ZeroMQ Subscriber (Server side)
Socket subscriber(context, ZMQ_PULL);

// ZeroMQ Push socket (Server side)
Socket pushSocket(context, ZMQ_PUSH);

// Utility variables
uchar data[];
ZmqMsg request;

// Variables for price subscription
string subscribedSymbols[];
int numSubscribedSymbols = 0;
datetime lastUpdateTime = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   EventSetMillisecondTimer(MILLISECOND_TIMER);
   
   // Set up publisher socket
   publisher.bind(StringFormat("%s://%s:%d", ZEROMQ_PROTOCOL, HOSTNAME, PUB_PORT));
   
   // Set up subscriber socket
   subscriber.bind(StringFormat("%s://%s:%d", ZEROMQ_PROTOCOL, HOSTNAME, PULL_PORT));
   
   // Set up push socket
   pushSocket.bind(StringFormat("%s://%s:%d", ZEROMQ_PROTOCOL, HOSTNAME, PUSH_PORT));
   
   // Initialize arrays
   ArrayResize(subscribedSymbols, 0);
   
   Print("[INFO] DWX ZeroMQ Server initialized");
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   
   // Shutdown ZeroMQ Context
   context.shutdown();
   context.destroy(0);
   
   Print("[INFO] DWX ZeroMQ Server stopped");
}

//+------------------------------------------------------------------+
//| Expert timer function                                            |
//+------------------------------------------------------------------+
void OnTimer()
{
   // Get client's request
   if (subscriber.recv(request, true))
   {
      // Get data from request
      string message = "";
      request.getData(data);
      message = CharArrayToString(data);
      
      // Process request
      ProcessRequest(message);
   }
   
   // Send price updates for subscribed symbols
   if (numSubscribedSymbols > 0 && (TimeCurrent() - lastUpdateTime) >= 1)
   {
      for (int i = 0; i < numSubscribedSymbols; i++)
      {
         SendPriceUpdate(subscribedSymbols[i]);
      }
      
      lastUpdateTime = TimeCurrent();
   }
}

//+------------------------------------------------------------------+
//| Process client request                                           |
//+------------------------------------------------------------------+
void ProcessRequest(string request)
{
   Print("[REQUEST] " + request);
   
   // Split request into components
   string parts[];
   int numParts = StringSplit(request, '|', parts);
   
   if (numParts == 0)
   {
      // Try to parse as JSON
      if (StringFind(request, "{") >= 0)
      {
         ProcessJsonRequest(request);
         return;
      }
      
      SendError("Invalid request format");
      return;
   }
   
   string command = parts[0];
   
   // Process different command types
   if (command == "GET_RATES")
   {
      if (numParts < 4)
      {
         SendError("Invalid GET_RATES request format");
         return;
      }
      
      string symbol = parts[1];
      string timeframe = parts[2];
      int count = (int)StringToInteger(parts[3]);
      
      SendHistoricalData(symbol, timeframe, count);
   }
   else if (command == "GET_PRICE")
   {
      if (numParts < 2)
      {
         SendError("Invalid GET_PRICE request format");
         return;
      }
      
      string symbol = parts[1];
      SendPriceUpdate(symbol);
   }
   else if (command == "SUBSCRIBE")
   {
      if (numParts < 2)
      {
         SendError("Invalid SUBSCRIBE request format");
         return;
      }
      
      string symbolsStr = parts[1];
      string symbols[];
      int numSymbols = StringSplit(symbolsStr, ',', symbols);
      
      for (int i = 0; i < numSymbols; i++)
      {
         SubscribeSymbol(symbols[i]);
      }
      
      // Send confirmation
      string response = "{\"_action\":\"SUBSCRIBE_CONFIRM\",\"_symbols\":\"" + symbolsStr + "\"}";
      SendResponse(response);
   }
   else if (command == "UNSUBSCRIBE")
   {
      if (numParts < 2)
      {
         SendError("Invalid UNSUBSCRIBE request format");
         return;
      }
      
      string symbolsStr = parts[1];
      
      if (symbolsStr == "ALL")
      {
         // Unsubscribe from all symbols
         ArrayResize(subscribedSymbols, 0);
         numSubscribedSymbols = 0;
      }
      else
      {
         string symbols[];
         int numSymbols = StringSplit(symbolsStr, ',', symbols);
         
         for (int i = 0; i < numSymbols; i++)
         {
            UnsubscribeSymbol(symbols[i]);
         }
      }
      
      // Send confirmation
      string response = "{\"_action\":\"UNSUBSCRIBE_CONFIRM\",\"_symbols\":\"" + symbolsStr + "\"}";
      SendResponse(response);
   }
   else if (command == "GET_ACCOUNT_INFO")
   {
      SendAccountInfo();
   }
   else if (command == "CLOSE_ORDER")
   {
      if (numParts < 2)
      {
         SendError("Invalid CLOSE_ORDER request format");
         return;
      }
      
      int ticket = (int)StringToInteger(parts[1]);
      CloseOrder(ticket);
   }
   else if (command == "GET_SYMBOLS")
   {
      SendSymbolsList();
   }
   else if (command == "STATUS")
   {
      // Send server status
      string response = "{\"_action\":\"STATUS\",\"status\":\"running\",\"version\":\"1.0\"}";
      SendResponse(response);
   }
   else
   {
      SendError("Unknown command: " + command);
   }
}

//+------------------------------------------------------------------+
//| Process JSON request                                             |
//+------------------------------------------------------------------+
void ProcessJsonRequest(string jsonRequest)
{
   // For now, we only support TRADE action in JSON format
   if (StringFind(jsonRequest, "\"_action\":\"TRADE\"") >= 0)
   {
      // Extract order details from JSON
      string orderType = ExtractJsonValue(jsonRequest, "_type");
      string symbol = ExtractJsonValue(jsonRequest, "_symbol");
      double volume = StringToDouble(ExtractJsonValue(jsonRequest, "_volume"));
      double price = StringToDouble(ExtractJsonValue(jsonRequest, "_price"));
      double stopLoss = StringToDouble(ExtractJsonValue(jsonRequest, "_sl"));
      double takeProfit = StringToDouble(ExtractJsonValue(jsonRequest, "_tp"));
      string comment = ExtractJsonValue(jsonRequest, "_comment");
      int magic = (int)StringToInteger(ExtractJsonValue(jsonRequest, "_magic"));
      
      // Place the order
      PlaceOrder(orderType, symbol, volume, price, stopLoss, takeProfit, comment, magic);
   }
   else
   {
      SendError("Unsupported JSON request");
   }
}

//+------------------------------------------------------------------+
//| Extract value from JSON string                                   |
//+------------------------------------------------------------------+
string ExtractJsonValue(string jsonString, string key)
{
   key = "\"" + key + "\":";
   int pos = StringFind(jsonString, key);
   
   if (pos < 0)
      return "";
      
   pos += StringLen(key);
   
   // Skip whitespace
   while (StringGetCharacter(jsonString, pos) == ' ')
      pos++;
   
   // Check if value is a string
   if (StringGetCharacter(jsonString, pos) == '"')
   {
      // Extract string value
      pos++;
      int endPos = StringFind(jsonString, "\"", pos);
      
      if (endPos < 0)
         return "";
         
      return StringSubstr(jsonString, pos, endPos - pos);
   }
   else
   {
      // Extract numeric or boolean value
      int endPos = StringFind(jsonString, ",", pos);
      
      if (endPos < 0)
         endPos = StringFind(jsonString, "}", pos);
         
      if (endPos < 0)
         return "";
         
      return StringSubstr(jsonString, pos, endPos - pos);
   }
}

//+------------------------------------------------------------------+
//| Send historical data                                             |
//+------------------------------------------------------------------+
void SendHistoricalData(string symbol, string timeframeStr, int count)
{
   // Convert timeframe string to timeframe value
   int timeframe = GetTimeframeValue(timeframeStr);
   
   if (timeframe == 0)
   {
      SendError("Invalid timeframe: " + timeframeStr);
      return;
   }
   
   // Prepare JSON response
   string response = "{\"_action\":\"RATES\",\"_symbol\":\"" + symbol + "\",\"_timeframe\":\"" + timeframeStr + "\",\"_data\":[";
   
   // Get historical data
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   
   int copied = CopyRates(symbol, timeframe, 0, count, rates);
   
   if (copied <= 0)
   {
      SendError("Failed to get historical data for " + symbol);
      return;
   }
   
   // Format data as JSON array
   for (int i = 0; i < copied; i++)
   {
      if (i > 0)
         response += ",";
         
      response += "{";
      response += "\"time\":" + IntegerToString(rates[i].time) + ",";
      response += "\"open\":" + DoubleToString(rates[i].open, 8) + ",";
      response += "\"high\":" + DoubleToString(rates[i].high, 8) + ",";
      response += "\"low\":" + DoubleToString(rates[i].low, 8) + ",";
      response += "\"close\":" + DoubleToString(rates[i].close, 8) + ",";
      response += "\"volume\":" + DoubleToString(rates[i].tick_volume, 0);
      response += "}";
   }
   
   response += "]}";
   
   SendResponse(response);
}

//+------------------------------------------------------------------+
//| Send current price update                                        |
//+------------------------------------------------------------------+
void SendPriceUpdate(string symbol)
{
   double bid = MarketInfo(symbol, MODE_BID);
   double ask = MarketInfo(symbol, MODE_ASK);
   
   if (bid == 0 || ask == 0)
   {
      // Invalid symbol or no price
      return;
   }
   
   string response = "{";
   response += "\"_action\":\"PRICE\",";
   response += "\"_symbol\":\"" + symbol + "\",";
   response += "\"_bid\":" + DoubleToString(bid, 8) + ",";
   response += "\"_ask\":" + DoubleToString(ask, 8) + ",";
   response += "\"_time\":" + IntegerToString(TimeCurrent());
   response += "}";
   
   SendResponse(response);
}

//+------------------------------------------------------------------+
//| Send account information                                         |
//+------------------------------------------------------------------+
void SendAccountInfo()
{
   string response = "{";
   response += "\"_action\":\"ACCOUNT_INFO\",";
   response += "\"_balance\":" + DoubleToString(AccountBalance(), 2) + ",";
   response += "\"_equity\":" + DoubleToString(AccountEquity(), 2) + ",";
   response += "\"_margin\":" + DoubleToString(AccountMargin(), 2) + ",";
   response += "\"_free_margin\":" + DoubleToString(AccountFreeMargin(), 2) + ",";
   response += "\"_leverage\":" + IntegerToString(AccountLeverage()) + ",";
   response += "\"_currency\":\"" + AccountCurrency() + "\"";
   response += "}";
   
   SendResponse(response);
}

//+------------------------------------------------------------------+
//| Send list of available symbols                                   |
//+------------------------------------------------------------------+
void SendSymbolsList()
{
   string response = "{\"_action\":\"SYMBOLS\",\"_data\":[";
   
   int symbolsCount = SymbolsTotal(false);
   
   for (int i = 0; i < symbolsCount; i++)
   {
      string symbol = SymbolName(i, false);
      
      if (i > 0)
         response += ",";
         
      response += "\"" + symbol + "\"";
   }
   
   response += "]}";
   
   SendResponse(response);
}

//+------------------------------------------------------------------+
//| Subscribe to symbol price updates                                |
//+------------------------------------------------------------------+
void SubscribeSymbol(string symbol)
{
   // Check if symbol is already subscribed
   for (int i = 0; i < numSubscribedSymbols; i++)
   {
      if (subscribedSymbols[i] == symbol)
         return;  // Already subscribed
   }
   
   // Add to subscribed symbols
   ArrayResize(subscribedSymbols, numSubscribedSymbols + 1);
   subscribedSymbols[numSubscribedSymbols] = symbol;
   numSubscribedSymbols++;
}

//+------------------------------------------------------------------+
//| Unsubscribe from symbol price updates                            |
//+------------------------------------------------------------------+
void UnsubscribeSymbol(string symbol)
{
   int index = -1;
   
   // Find symbol index
   for (int i = 0; i < numSubscribedSymbols; i++)
   {
      if (subscribedSymbols[i] == symbol)
      {
         index = i;
         break;
      }
   }
   
   if (index >= 0)
   {
      // Remove symbol from array
      for (int i = index; i < numSubscribedSymbols - 1; i++)
      {
         subscribedSymbols[i] = subscribedSymbols[i + 1];
      }
      
      numSubscribedSymbols--;
      ArrayResize(subscribedSymbols, numSubscribedSymbols);
   }
}

//+------------------------------------------------------------------+
//| Place a trading order                                            |
//+------------------------------------------------------------------+
void PlaceOrder(string orderType, string symbol, double volume, double price, 
                double stopLoss, double takeProfit, string comment, int magic)
{
   int cmd = -1;
   
   // Convert order type string to command
   if (orderType == "BUY")
      cmd = OP_BUY;
   else if (orderType == "SELL")
      cmd = OP_SELL;
   else if (orderType == "BUYLIMIT")
      cmd = OP_BUYLIMIT;
   else if (orderType == "SELLLIMIT")
      cmd = OP_SELLLIMIT;
   else if (orderType == "BUYSTOP")
      cmd = OP_BUYSTOP;
   else if (orderType == "SELLSTOP")
      cmd = OP_SELLSTOP;
   
   if (cmd < 0)
   {
      SendError("Invalid order type: " + orderType);
      return;
   }
   
   // For market orders, use current price
   if (cmd == OP_BUY)
      price = MarketInfo(symbol, MODE_ASK);
   else if (cmd == OP_SELL)
      price = MarketInfo(symbol, MODE_BID);
   
   // Place the order
   int ticket = OrderSend(symbol, cmd, volume, price, 5, stopLoss, takeProfit, comment, magic);
   
   if (ticket > 0)
   {
      // Order placed successfully
      string response = "{";
      response += "\"_action\":\"TRADE_CONFIRM\",";
      response += "\"_ticket\":" + IntegerToString(ticket) + ",";
      response += "\"_symbol\":\"" + symbol + "\",";
      response += "\"_type\":\"" + orderType + "\",";
      response += "\"_price\":" + DoubleToString(price, 8) + ",";
      response += "\"_time\":" + IntegerToString(TimeCurrent());
      response += "}";
      
      SendResponse(response);
   }
   else
   {
      // Order failed
      int error = GetLastError();
      SendError("Order failed with error " + IntegerToString(error) + ": " + ErrorDescription(error));
   }
}

//+------------------------------------------------------------------+
//| Close an open order                                              |
//+------------------------------------------------------------------+
void CloseOrder(int ticket)
{
   if (!OrderSelect(ticket, SELECT_BY_TICKET))
   {
      SendError("Order not found: " + IntegerToString(ticket));
      return;
   }
   
   if (OrderCloseTime() > 0)
   {
      SendError("Order already closed: " + IntegerToString(ticket));
      return;
   }
   
   bool success = false;
   
   // Close the order
   if (OrderType() == OP_BUY)
   {
      success = OrderClose(ticket, OrderLots(), MarketInfo(OrderSymbol(), MODE_BID), 5);
   }
   else if (OrderType() == OP_SELL)
   {
      success = OrderClose(ticket, OrderLots(), MarketInfo(OrderSymbol(), MODE_ASK), 5);
   }
   else
   {
      // For pending orders, just delete them
      success = OrderDelete(ticket);
   }
   
   if (success)
   {
      // Order closed successfully
      string response = "{";
      response += "\"_action\":\"CLOSE_CONFIRM\",";
      response += "\"_ticket\":" + IntegerToString(ticket);
      response += "}";
      
      SendResponse(response);
   }
   else
   {
      // Failed to close order
      int error = GetLastError();
      SendError("Failed to close order " + IntegerToString(ticket) + ": " + ErrorDescription(error));
   }
}

//+------------------------------------------------------------------+
//| Send error message                                               |
//+------------------------------------------------------------------+
void SendError(string message)
{
   string response = "{\"_action\":\"ERROR\",\"_message\":\"" + message + "\"}";
   SendResponse(response);
}

//+------------------------------------------------------------------+
//| Send response to client                                          |
//+------------------------------------------------------------------+
void SendResponse(string response)
{
   // Print response for debugging
   Print("[RESPONSE] " + response);
   
   // Convert string to char array
   uchar responseData[];
   StringToCharArray(response, responseData);
   
   // Create ZeroMQ message
   ZmqMsg responseMsg(responseData);
   
   // Send the message
   pushSocket.send(responseMsg);
}

//+------------------------------------------------------------------+
//| Convert timeframe string to timeframe value                      |
//+------------------------------------------------------------------+
int GetTimeframeValue(string timeframe)
{
   if (timeframe == "M1")
      return PERIOD_M1;
   else if (timeframe == "M5")
      return PERIOD_M5;
   else if (timeframe == "M15")
      return PERIOD_M15;
   else if (timeframe == "M30")
      return PERIOD_M30;
   else if (timeframe == "H1")
      return PERIOD_H1;
   else if (timeframe == "H4")
      return PERIOD_H4;
   else if (timeframe == "D1")
      return PERIOD_D1;
   else if (timeframe == "W1")
      return PERIOD_W1;
   else if (timeframe == "MN1")
      return PERIOD_MN1;
   
   return 0;  // Invalid timeframe
}

