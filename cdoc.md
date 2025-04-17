## here i will try to include all the documentation from https://help.ctrader.com/open-api/.

1. Getting Started¶
The cTrader Open API is a service you can use to develop custom applications connected to the cTrader backend. This documentation provides everything you need to know including information about SDKs, structured tutorials, code snippets, and more.

What Is Open API?¶
The cTrader Open API is a service that allows anyone with a cTID to create an application sending and receiving information to and from the cTrader backend. You can use this API to develop trading-oriented apps or services or integrate the cTrader backend with any existing solutions you may have.

Using this API involves sending and receiving messages to and from the cTrader backend. This is done via sending/receiving either JSON objects or Google Protocol Buffers (Protobufs). Both of these means of data serialisation/deserialisation are language-neutral, meaning that you can use any programming language you want to interact with the API.

Message Names

Note that when this documentation references specific messages (e.g., ProtoOAApplicationAuthReq), it uses the Protobuf notation with ProtoOA... at the start of a message name.

The cTrader Open API is available for anyone registered with a cTrader-affiliated broker.

Use Cases

Here are just some of the possible applications you may create when interacting with the cTrader Open API.

A custom trading application that funnels new users to create new accounts with a certain broker.
A Telegram bot that automatically informs your followers of any new traders you may have placed.
An app for wearables that displays the current P&L of the five most recent positions opened by the user.
A mobile app that gives a market overview by using a generative AI service.
As you can see, the cTrader Open API is perfect for professional traders who want to go social and closely interact with their followers.

Essential Functionality¶
Here is a non-exhaustive list of what the cTrader Open API allows your code to do.

Access real-time market data.
Perform all possible types of trading operations permitted in the official cTrader applications.
Retrieve and process information on past, current, and pending operations including deals, orders, and positions.
As shown in our Terms of Use, the API can be accessed by anyone with a cTID, and, by default, it is supported by all trading accounts of any cTrader-affiliated brokers.

Rate Limiting

Note that there exist some limits on how frequently you can perform certain requests to the cTrader backend.

You can perform a maximum of 50 requests per second per connection for any non-historical data requests.
You can perform a maximum of 5 requests per second per connection for any historical data requests.
Demo and Live Trading¶
You can use the cTrader Open API to trade on behalf of both Demo and Live accounts.

We recommend using Demo accounts for development and testing, and then switching to Live after making sure that your integration with the cTrader Open API works as intended.

However, there are no hard restrictions, and you may freely choose to start development and testing under a Live account.

SDKs¶
When integrating with the Open API, you can use either JSON or Protobufs for data serialisation/deserialisation.

You can use any language to implement the cTrader Open API. However, if you intend to use Protobufs, we highly recommend using a language that has official SDK support from Spotware. To date, these languages are as follows.

C# (access the SDK here)
Python (access the SDK here)
Every official SDK listed above contains 'helper' methods and classes that make the implementation of the cTrader Open API as smooth as possible.

If you intend to use JSON, there is no need to use our SDKs as handling serialisation/deserialisation in this case is relatively simple.


2. Use Cases¶
This guide highlights some practical aspects of creating custom applications by means of the cTrader Open API. We offer specific functionality examples, rate apps in terms of their complexity for developers, and review best practices below.

Types of Apps Created via Open API¶
The cTrader Open API allows developers to create various application types. Possible examples include:

Custom trading apps. You can build your own trading platform that will be connected to the cTrader backend. It may differentiate in terms of personalised features, custom user interfaces, and functionality tailored to specific trading strategies or user preferences.
Technical analysis tools. It is possible to develop apps that source and analyse real-time market data offering visualisation and insight for trading decisions as a custom-made output.
Telegram bots. Existing cTrader users can be provided with the functionality to place different order types with specified parameters via a Telegram bot.
Apps for wearable devices. One can create an app for smartwatches that would display the user’s current P&L. Customisable notification settings are usually provided by products of this type.
AI-based assistants. Developers can request generative AI services to process historical prices and identify trends relying on statistical analysis. It is possible to match breaking news and market dynamics.
Price alert systems. It is possible to build apps notifying users about specific market conditions and price levels. Some functionality to react to these events can be offered by developers.
Strategy improvement tools. Apps that allow users to trade on historical data for testing and improving their strategies in different modes can be created due to the cTrader Open API. The outcomes should prompt how to optimise and refine individual strategies.
Perceived Complexity and App Functionality¶
Different levels of complexity are attributed to the exemplified application types. The following chart accounts for their perceived complexity and offers some functionality examples.

App Types	Perceived Complexity	Functionality Examples
Custom trading apps	★ ★ ★ ★ ★	Attaining live bars data and live quotes, placing and executing orders, closing positions, modifying pending orders, converting symbol rates, calculating P&L.
Technical analysis tools	★ ★ ★	Offering interactive chart capabilities, drawing trendlines and other visuals, recognising chart patterns automatically, and applying risk management tools.
Telegram bots	★ ★	Retrieving account balance information, placing orders, closing positions, notifying about the status of the current orders/positions, and canceling orders.
Apps for wearables	★ ★ ★	Calculating P&L, closing positions, modifying pending orders, obtaining balance and equity data, and receiving price alerts.
AI-based assistants	★ ★	Accessing historical bars and tick data, recognising meaningful patterns in historical data, matching historical drawdowns and price dynamics, refining strategy suggestions, and estimating entrance/exit points.
Price alert systems	★	Receiving live bars data and live quotes, reacting to specific price levels, sending notifications and alerts, and adjusting alert sensitivity.
Strategy improvement tools	★ ★ ★ ★	Obtaining historical bars and tick data, calculating P&L, backtesting strategies, analysing strategy performance, optimising order parameters and protection mechanisms, assessing trading risks, testing multiple scenarios, and replaying market situations.
Best Practices for Creating Apps¶
There are a number of best practices that can facilitate the process of application development.

Understand your users’ requirements. Before developing a custom trading app, deeply research into the unaddressed user needs it should satisfy in your preferred market. Why is the cTrader standard functionality redundant or insufficient for your target audience? For example, the order placement functionality should be simplified to a bare minimum to retain even first-time traders.

Study the cTrader Open API. Familiarising yourself with the Open API documentation will provide you with crucial insight into opportunities and features your app can deliver. If your custom trading app or Telegram bot needs to display P&L in an exotic currency, you should know how to request a necessary conversion chain.

Design a user-friendly UI. Aim at a clean and intuitive UI that would provide easy navigation, effective data visualisation, and seamless interaction with the trading platform. Apps for wearable devices are especially demanding in terms of a convenient UI since their screens are small, which may challenge functionality. The UI should also prompt how to interact with the app by means of gestures, swiping, and tapping. On mobile platforms, consider different viewport sizes to ensure that the UI is displayed as planned on different devices.

Improve security. Applications that request to authorise trading account sessions and place orders on behalf of registered cTrader users (e.g., Telegram bots) should adopt industry-standard security practices. To securely store your access token, you can use HTTP-only cookies, which cannot be accessed by JavaScript and are more difficult to be stolen via cross-site scripting (XSS) attacks. An additional level of security is possible due to SameSite cookies, the Secure attribute of your cookies, or the token binding technique. When developing .NET applications for Windows, you can use DPAPI for securely storing the access token. On mobile devices, use biometric authentication methods, such as fingerprints and facial recognition. Additionally, you can require two-factor authentication for your users.

Personalise features. As long as you are developing technical analysis instruments, offer something unique in terms of a customisable layout and adjustable chart preferences. Your users will enjoy having personalised presets, templates, and colour schemes. You may consider integrating a customisable calendar of upcoming financial events and news releases that potentially influence price dynamics.

Implement real-time updates. For applications such as price alert systems, it is pivotal to receive real-time data updates to realistically reflect the latest market prices. Implement a stable connection to the cTrader backend and minimise latency. Develop an emergency plan and reserve solutions for managing potential connection disruptions.

Test extensively. AI-based assistants and strategy improvement tools should be extensively tested on historical data before their full-scale launch. ‘Train’ your application to recognise different trading scenarios and market conditions. Integrating historical data playback would be beneficial to your app in terms of a realistic market simulation of trading conditions. Within a strategy improvement environment, you may give users the option to trade on tick or bar data.

Provide comprehensive documentation. Carefully document the functionalities, features, and API integrations of your application. Doing so will increase your users’ independence and confidence. Additionally, you will be able to reduce pressure on your support team. Ideally, video guides and FAQs should be available to your users.

Engage in the cTrader community. Share knowledge, seek advice, and collaborate with the cTrader developer community. Participating in forum and Telegram channel discussions, you will manage to upgrade your app functionality and resolve any challenges you may encounter.

To summarise in the end, the provided list of application types and best practices is not exhaustive, and you can go beyond by implementing your original ideas due to the cTrader Open API.


3. Creating Your Application¶
Creating your application from scratch may seem daunting. To make this process significantly less challenging, you can divide it into smaller steps, forming an easy-to-follow roadmap.

Below, we provide the key stages that this roadmap could include.

Choose the purpose of your application

Define the key functionality and processes

Create the application UI

Register your application

Code the key functionality

Debug and test your application

Deploy and distribute your application

Choose the Purpose of Your Application¶
For your app to be downloaded and used, it has to deliver value to the end users. As a result, any good application starts with defining the need it is supposed to address.

Addressing User Needs

Here are some examples of the user needs you may choose to address.

Traders may want to keep track of their performance all the time, not just inside cTrader. An app for wearable devices may prove very successful.
Users with a followership could need a way to automatically inform their subscribers of new trades. You can easily provide such functionality using the cTrader Open API and an API provided by a popular messenger service.
Pro traders who partner with a broker may want a custom trading terminal that funnels users into creating new accounts with this broker. By integrating with the Open API you can easily satisfy this request.
The purpose of your application does not necessarily have to be unique but it has to be specific and achievable.

Define the Key Functionality and Processes¶
After deciding on the need that your application will address, you should create a simple bullet point list outlining its key functionality.

This bullet point list should not be very long (four-five points maximum) and should answer the following questions.

What information will my app show to end users?
What actions should end users be able to perform inside the application?
What controls will my application have for end users to interact with?
Being Mindful of Constraints

When answering the questions above, always keep in mind the limitations imposed by your preferred programming language and/or UI framework.

Create the Application UI¶
You now know what your app is supposed to do and what essential features it will include. The next logical step is to create its UI. Broadly speaking, this process usually involves the following.

Defining the parameters of the devices where your app will be displayed (e.g., typical screen sizes).
Creating mockups of all the key screens. This can be done either by hand using a pen and paper or via a 'wireframe' software solution.
'Cleaning up' your mockups and turning them into a set of screens containing all major controls. You can outsource this step to a professional graphic designer if you have such an opportunity.
Register Your Application¶
After deciding the purpose of your application and its key functionality, you should be ready to register the service at the cTrader Open API Portal. You can read a detailed overview of this process in a separate guide.

As detailed in our guide to app and account authentication, do not forget to specify a valid redirect URL for

Describing Your Application

When registering your application, make sure to provide as many details as possible. Spotware carefully evaluates new Open API services and there is a higher chance of your application getting approved if you explicitly describe why it is needed and what it will allow users to do.

Code the Key Functionality¶
After receiving approval from Spotware, you should proceed with coding your application. As usual, we recommend using the official cTrader Open API SDKs as they contain helpful methods and classes allowing you to save time on implementing essential features.

Here is a small roadmap you can follow when coding a new application.

Create a system for opening a connection.
Establish a connection to a proxy.
Add a solution for sending/receiving messages.
Implement a service for app and account authentication.
Add custom logics that handle the functionality of your app.
Debug and Test Your Application¶
Debugging is essential for ensuring that your app behaves as expected. Any modern IDE typically allows for setting breakpoints at certain lines in your code so that you can easily see how your commands are executed. When a breakpoint is hit, execution is paused until you resume it manually.

If you have such an opportunity, you could also recruit your friends as impromptu quality assurance engineers. They can review how your application behaves on different devices and identify errors that would have been difficult to spot when simply debugging by yourself.

Deploy and Distribute Your Application¶
The process of deployment essentially means making your app available to end users. The details of this process depend on the platform that your app is supposed to run on.

For desktop devices you can simply build your application in release mode and add a custom installer.
For Android smartphones, you have to sign and release your application following the official Google guidelines.
For iOS devices, you first need to prepare the app bundle and register your service on App Store Connect.
For a web project, choose a suitable deployment service (e.g., AWS Elastic Beanstalk) and follow its guidelines. Alternatively, procure suitable hosting and deploy your app on a remote server.


4. Serialising and Deserialising Messages¶
To serialise/deserialise messages sent to and from the cTrader backend, you can use either Protocol Buffers (Protobufs) or JSON (JavaScript Object Notation).

Protobufs vs JSON

You may want to consider using JSON in the following cases.

If you want to simplify integration as much as possible. JSON is easy-to-use, allowing you to serialise messages into human-readable strings.
If you have used JSON in the past when integrating with other APIs. In that case, you may want to stick to the format that you are most familiar with.
In contrast, you may choose to use Protobufs in the following cases.

If you want to make your integration as lightweight as possible. Protobuf messages are compact and, therefore, serialisation/deserialisation is faster compared to JSON.
If you intend to mostly rely on the official SDKs as they provide helpful methods and classes that you can use to abstract the most complex parts of working with Protobufs.
Open API Messages

All messages you can use in your integration can be found in the messages Github repo.

Below, we define each method of serialisation/deserialisation in detail.

JSON¶
JSON objects can be defined as simple key-value pairs. Note that keys are always strings while values can be of different data types as shown in the below example.

{
    "clientMsgId": "cm_id_2",
    "payloadType": 2100,
    "payload": {
        "keyOne": [1, 2, 10,],
        "keyTwo": "valueTwo",
    }
}
In the example, the value of the "clientMsgId" key is a string while the value of the "payloadType" key is an integer. The "payload" key contains another JSON object which is nested in the body of the 'parent' object. The value of the "payload.keyOne" key is a list of integers.

Connecting to the Required Port

Note that you can only operate with JSON if you connect to port 5036 when establishing a connection with the cTrader backend.

For a tutorial on how you can send/receive JSON, click here.

Protocol Buffers¶
Protocol Buffers (or Protobufs) offer a language and platform-neutral, extensible mechanism for serialising structured data. By using Protobufs, you can encode structured data in an efficient yet extensible format.

With Protobufs, you only need to define how you want your data to be structured once. This is done by specifying Protobuf message types in .proto files.

Each Protobuf message is a record of information containing a series of name-value pairs. Below, you can find a basic example of a .proto file that defines a message containing information about a person.

message Person {

    required string name = 1;  
    required int32 id = 2;  
    optional string email = 3;  


    enum PhoneType {  
        MOBILE = 0;  
        HOME = 1;  
        WORK = 2;  
    }  

    message PhoneNumber {  
       required string number = 1;  
       optional PhoneType type = 2 [default = HOME];  
    }  

    repeated PhoneNumber phone = 4;  
}
As you can see, the message format is simple. Each message type has one or more uniquely numbered fields, and each field has a name and a value type, where value types can be numbers (integer or floating-point), booleans, strings, raw bytes, or even (as in the example above) other Protocol Buffer message types, allowing you to structure your data hierarchically.

You can find more information about writing .proto files in the Protocol Buffer Language Guide.

You can learn more about Protocol Buffers here.

Note

Note that the cTrader Open API uses Protocol Buffers version 2 syntax. However, you can still use the latest versions of your chosen Protocol Buffers compiler/SDKs as they are backward compatible and work with both version 2 and version 3 message files.

For a tutorial on sending/receiving Protobufs, click here.

ProtoMessages¶
When working with Protobufs, you will be sending and receiving ProtoMessage objects designed by Spotware.

To handle network fragmentation, sending messages uses the following frame structure.

 +--------------------------+-----------------------------------------+  
 | Message Length (4 bytes) | Serialized ProtoMessage object (byte[]) |  
 +--------------------------+-----------------------------------------+  
                            |<---------- Message Length ------------->|
Note

The system architecture is little-endian (that is, little end first), which means that you must reverse the length bytes when sending and receiving data.

Each ProtoMessage has the following structure.

 +----------------------+  
 | int32 payloadType    |  
 | byte[] payload       |  
 | string clientMsgId   |  
 +----------------------+
The structure contains two mandatory fields.

payloadType. Contains the ProtoPayloadType ID. This field denotes the type of the Protobuf object serialised in the payload field.
payload. Contains the actual serialised Protobuf message that corresponds to payloadType.
One other field is optional.

clientMsgId. Contains the message ID which is assigned by the client.
The actual `ProtoMessage`` definition looks as follows.

message ProtoMessage {  
    required uint32 payloadType = 1; //Contains the ID of the ProtoPayloadType or other
    custom PayloadTypes (e.g. ProtoCHPayloadType).  
    optional bytes payload = 2; //The serialised Protobuf message that corresponds to
    the payloadType.  
    optional string clientMsgId = 3; //The request message ID which is assigned by the
    client.  
}
Naming Convention¶
The Protobuf messages that form the cTrader Open API can be categorised into the following types.

Request messages
Response messages
Event messages
Model messages
Request Messages¶
Request messages are used to ask the cTrader backend for information or perform various operations.

Request messages are marked with Req at the end of their respective names. For example, the ProtoOAAssetListReq message requests the cTrader backend to return a list of all assets available for trading to a currently authorised account.

Response Messages¶
Response messages mark data that is received from the cTrader backend.

Response messages are marked with Res at the end of their respective names. As an illustration, the ProtoOAAssetListRes message has a repeated field (asset) that contains all assets that the currently authorised account can trade.

Event Messages¶
Event messages asynchronously notify all their subscribers that a particular event has been triggered.

Event messages are marked with Event at the end of their respective names. For instance, the ProtoOAMarginChangedEvent is sent every time when the amount of margin allocated to a specific position is changed.

Model Messages¶
Model messages describe the entities that form the domain model in the cTrader backend.

The names of model messages always end with the name of the entity that they are defining. As an example, the ProtoOAAsset message defines the Asset entity.

Messages Repository¶
You can download the latest version of the cTrader Open API Protocol Buffers message files from this repository.

We recommend you follow the messages repository if you want to get notified whenever a new version of the message files is released.

Compiling Protobuf Messages¶
Once you attain the required Protobuf messages, you can run the Protobuf compiler for your chosen language on the .proto files defining these messages. On success, the compiler will generate data access classes in your preferred language.

These classes provide simple accessors for each field (such as name() and set_name()) as well as methods for handling serialisation and deserialisaition. The name of each class should match the full name of each message that was compiled. At this point, you can freely use the generated classes in your application to populate, serialise and deserialise Protobuf messages.

To learn more about compiling protobuf messages using your language of choice, click here.


5. Registering a New Application¶
To integrate with the cTrader Open API you will first need to register an application. You will be required to use the application credentials for accessing the API.

Creating a New Application¶
To create a new API application, perform the following actions.

1. Open the cTrader Open API portal.

2. Log in using your cTrader ID.

3. After logging in, open the 'Applications' page.

4. Click on the 'Add New App' button.

5. Fill out the application form.

Fast Approval

To ensure your application gets approved as quickly as possible, please provide its detailed description.

6. Click on 'Save'.

Afterward, the newly created application will appear in the applications list. Its status will be set to 'Submitted'

After the application is reviewed by Spotware, you will be contacted via email. The message will either confirm the application approval or request further details about your application.

Adding Redirect URIs¶
Once your application is approved by Spotware, you can start integrating with the cTrader Open API.

The next step is to add a redirect URI that will be used for account authentication.

Note that you can always change the redirect URIs assigned to your application, remove them entirely, or add new ones.

The Default Redirect URI

The default redirect URI is only for the playground environment. As it does not work outside the playground environment, you cannot use it in your code.

April 11, 2025
Copyright © 2025 Spotware Systems Ltd. cTrader, cAlgo, cBroker, cMirror. All rights reserved.

6. Error Handling¶
Error handling is a crucial part of any reliable and user-friendly Open API application. Unless you catch and process various errors, your users may experience 'janky' UI or may be prevented from performing certain essential actions entirely.

Broadly speaking, different error handling processes may be implemented depending on the layer where an error occurs.

At the data/domain layer. In some cases, the cTrader backend may send the ProtoErrorRes message as a response to one of your requests. For operations related to orders, deals, or positions, you may also receive the ProtoOAOrderErrorEvent message.
At the domain/application layer. Users may perform actions that you have not accounted for in your code, resulting in your application behaving unexpectedly.
The mechanisms for handling errors at these levels are different and are described below.

Error Handling at the Data/Domain Layer¶
You may receive ProtoErrorRes or ProtoOAOrderErrorEvent in the following situations (note that the list is not exhaustive).

Attempting to place an order for a symbol for which the market is closed.
Sending an incorrect or an unsupported message.
Attempting to modify an order that is being executed.
Sending a message after losing your connection to the cTrader backend.
Analysing Errors

Both the ProtoErrorRes and the ProtoOAOrderErrorEvent have the errorCode and description fields that contain precise information about the type of error that has occurred and its description. You can see the full list of all supported error codes in the ProtoErrorCode enum.

To make sure that your application does not 'break' in such cases, you can usually subscribe to callbacks that trigger when you receive an error response. The exact logic of these callbacks as well as how you can subscribe to them depend on the client you are using to establish a connection and listen to the messages stream.

Working With JSON

When operating with JSON, you can still reuse code from this tutorial; however, you would need to slightly modify it depending on your approach to serialisation/deserialisation and your preferred TCP/WebSocket client.


C#
Python
private void SubscribeToErrors(IObservable<IMessage> observable)
{
    if (observable is null) throw new ArgumentNullException(nameof(observable));

    observable.ObserveOn(SynchronizationContext.Current).Subscribe(_ => { }, OnError);
    observable.OfType<ProtoErrorRes>().ObserveOn(SynchronizationContext.Current).Subscribe(OnErrorRes);

    observable.OfType<ProtoOAOrderErrorEvent>().ObserveOn(SynchronizationContext.Current).Subscribe(OnOrderErrorRes);
}

private void OnOrderErrorRes(ProtoOAErrorRes error)
{
    Console.WriteLine($"Error: Error {error.ErrorCode}; {error.Description}");
}

private void OnErrorRes(ProtoErrorRes error)
{
    Console.WriteLine($"Error: Error {error.ErrorCode}; {error.Description}");
}

Error Handling at the Domain/Application Layer¶
The way you handle errors at the domain and application layers depends on your chosen programming language, UI framework, and the use cases you implement, making it difficult to provide specific code snippets and solutions.

However, the following recommendations can prove useful regardless of how you choose to integrated with the cTrader Open API.

Always implemented a dedicated error state for major UI elements. This would prevent your application from 'breaking' entirely and allow for running in a semi-degradated state.
Implement a secure and reliable logging mechanism that would record errors in a suitable location (e.g., local storage). If repeated errors occur, logging should simplify identifying and addressing their cause.
Create a mechanism for users to inform you of errors. This can be as simple as providing your contact info within the application or as complicated as adding an automatic feedback submission service that triggers on new errors.
Ensure that any resources used when errors occur are properly cleaned up. While most languages offer 'garbage collector' services, you may want to specify custom resource disposal logics.



7. Messages¶
ProtoOAAccountAuthReq¶
Request for authorizing of the trading account session.

Requires established authorized connection with the client application using ProtoOAApplicationAuthReq.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	The unique identifier of the trader's account in cTrader platform.
accessToken	string	Required	The Access Token issued for providing access to the Trader's Account.
ProtoOAAccountAuthRes¶
Response to the ProtoOAApplicationAuthRes request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	The unique identifier of the trader's account in cTrader platform.
ProtoOAAccountDisconnectEvent¶
Event that is sent when the established session for an account is dropped on the server side.

A new session must be authorized for the account.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	The unique identifier of the trader's account in cTrader platform.
ProtoOAAccountLogoutReq¶
Request for logout of trading account session.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	The unique identifier of the trader's account in cTrader platform.
ProtoOAAccountLogoutRes¶
Response to the ProtoOAAccountLogoutReq request.

Actual logout of trading account will be completed on ProtoOAAccountDisconnectEvent.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	The unique identifier of the trader's account in cTrader platform.
ProtoOAAccountsTokenInvalidatedEvent¶
Event that is sent when a session to a specific trader's account is terminated by the server but the existing connections with the other trader's accounts are maintained.

Reasons to trigger: account was deleted, cTID was deleted, token was refreshed, token was revoked.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountIds	RepeatedField<int64>	Repeated	The unique identifier of the trader's account in cTrader platform.
reason	string	Optional	The disconnection reason explained. For example: Access Token is expired or recalled.
ProtoOAAmendOrderReq¶
Request for amending the existing pending order.

Allowed only if the Access Token has "trade" permissions for the trading account.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
orderId	int64	Required	The unique ID of the order.
volume	int64	Optional	Volume, represented in 0.01 of a unit (e.g. 1000 in protocol means 10.00 units).
limitPrice	double	Optional	The Limit Price, can be specified for the LIMIT order only.
stopPrice	double	Optional	The Stop Price, can be specified for the STOP and the STOP_LIMIT orders.
expirationTimestamp	int64	Optional	The Unix timestamp in milliseconds of Order expiration. Should be set for the Good Till Date orders.
stopLoss	double	Optional	The absolute Stop Loss price (e.g. 1.23456). Not supported for MARKET orders.
takeProfit	double	Optional	The absolute Take Profit price (e.g. 1.23456). Not supported for MARKET orders.
slippageInPoints	int32	Optional	Slippage distance for the MARKET_RANGE and the STOP_LIMIT orders.
relativeStopLoss	int64	Optional	The relative Stop Loss can be specified instead of the absolute one. Specified in 1/100000 of a unit of price. (e.g. 123000 in protocol means 1.23, 53423782 means 534.23782) For BUY stopLoss = entryPrice - relativeStopLoss, for SELL stopLoss = entryPrice + relativeStopLoss.
relativeTakeProfit	int64	Optional	The relative Take Profit can be specified instead of the absolute one. Specified in 1/100000 of a unit of price. (e.g. 123000 in protocol means 1.23, 53423782 means 534.23782) For BUY takeProfit = entryPrice + relativeTakeProfit, for SELL takeProfit = entryPrice - relativeTakeProfit.
guaranteedStopLoss	bool	Optional	If TRUE then the Stop Loss is guaranteed. Available for the French Risk or the Guaranteed Stop Loss Accounts.
trailingStopLoss	bool	Optional	If TRUE then the Trailing Stop Loss is applied.
stopTriggerMethod	ProtoOAOrderTriggerMethod	Optional	Trigger method for the STOP or the STOP_LIMIT pending order.
ProtoOAAmendPositionSLTPReq¶
Request for amending StopLoss and TakeProfit of existing position.

Allowed only if the accessToken has "trade" permissions for the trading account.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
positionId	int64	Required	The unique ID of the position to amend.
stopLoss	double	Optional	Absolute Stop Loss price (1.23456 for example).
takeProfit	double	Optional	Absolute Take Profit price (1.26543 for example).
guaranteedStopLoss	bool	Optional	If TRUE then the Stop Loss is guaranteed. Available for the French Risk or the Guaranteed Stop Loss Accounts.
trailingStopLoss	bool	Optional	If TRUE then the Trailing Stop Loss is applied.
stopLossTriggerMethod	ProtoOAOrderTriggerMethod	Optional	The Stop trigger method for the Stop Loss/Take Profit order.
ProtoOAApplicationAuthReq¶
Request for the authorizing an application to work with the cTrader platform Proxies.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
clientId	string	Required	The unique Client ID provided during the registration.
clientSecret	string	Required	The unique Client Secret provided during the registration.
ProtoOAApplicationAuthRes¶
Response to the ProtoOAApplicationAuthReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ProtoOAAssetClassListReq¶
Request for a list of asset classes available for the trader's account.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
ProtoOAAssetClassListRes¶
Response to the ProtoOAAssetListReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
assetClass	RepeatedField<ProtoOAAssetClass>	Repeated	List of the asset classes.
ProtoOAAssetListReq¶
Request for the list of assets available for a trader's account.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
ProtoOAAssetListRes¶
Response to the ProtoOAAssetListReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
asset	RepeatedField<ProtoOAAsset>	Repeated	The list of assets.
ProtoOACancelOrderReq¶
Request for cancelling existing pending order.

Allowed only if the accessToken has "trade" permissions for the trading account.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
orderId	int64	Required	The unique ID of the order.
ProtoOACashFlowHistoryListReq¶
Request for getting Trader's historical data of deposits and withdrawals.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
fromTimestamp	int64	Required	The Unix time from which the search starts >=0 (1st Jan 1970). Validation: toTimestamp - fromTimestamp <= 604800000 (1 week).
toTimestamp	int64	Required	The Unix time where to stop searching <= 2147483646000 (19th Jan 2038).
ProtoOACashFlowHistoryListRes¶
Response to the ProtoOACashFlowHistoryListReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
depositWithdraw	RepeatedField<ProtoOADepositWithdraw>	Repeated	The list of deposit and withdrawal operations.
ProtoOAClientDisconnectEvent¶
Event that is sent when the connection with the client application is cancelled by the server.

All the sessions for the traders' accounts will be terminated.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
reason	string	Optional	The disconnection reason explained. For example: The application access was blocked by cTrader Administrator.
ProtoOAClosePositionReq¶
Request for closing or partially closing of an existing position.

Allowed only if the accessToken has "trade" permissions for the trading account.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
positionId	int64	Required	The unique ID of the position to close.
volume	int64	Required	Volume to close, represented in 0.01 of a unit (e.g. 1000 in protocol means 10.00 units).
ProtoOADealListByPositionIdReq¶
Request for retrieving the deals related to a position.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
positionId	int64	Required	The unique ID of the position.
fromTimestamp	int64	Optional	The Unix time in milliseconds of starting the search. Must be bigger or equal to zero (1st Jan 1970).
toTimestamp	int64	Optional	The Unix time in milliseconds of finishing the search. <= 2147483646000 (19th Jan 2038).
ProtoOADealListByPositionIdRes¶
Response to the ProtoOADealListByPositionIdReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
deal	RepeatedField<ProtoOADeal>	Repeated	The list of deals.
hasMore	bool	Required	If TRUE then the number of records by filter is larger than chunkSize, the response contains the number of records that is equal to chunkSize.
ProtoOADealListReq¶
Request for getting Trader's deals historical data (execution details).

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
fromTimestamp	int64	Optional	The Unix time from which the search starts >=0 (1st Jan 1970).
toTimestamp	int64	Optional	The Unix time where to stop searching <= 2147483646000 (19th Jan 2038).
maxRows	int32	Optional	The maximum number of the deals to return.
ProtoOADealListRes¶
The response to the ProtoOADealListRes request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
deal	RepeatedField<ProtoOADeal>	Repeated	The list of the deals.
hasMore	bool	Required	If TRUE then the number of records by filter is larger than chunkSize, the response contains the number of records that is equal to chunkSize.
ProtoOADealOffsetListReq¶
Request for getting sets of Deals that were offset by a specific Deal and that are offsetting the Deal.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
dealId	int64	Required	The unique ID of the Deal.
ProtoOADealOffsetListRes¶
Response for ProtoOADealOffsetListReq.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
offsetBy	RepeatedField<ProtoOADealOffset>	Repeated	Deals which closed the specified deal.
offsetting	RepeatedField<ProtoOADealOffset>	Repeated	Deals which were closed by the specified deal.
ProtoOADepthEvent¶
Event that is sent when the structure of depth of market is changed.

Requires subscription on the depth of markets for the symbol, see ProtoOASubscribeDepthQuotesReq.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
symbolId	uint64	Required	Unique identifier of the Symbol in cTrader platform.
newQuotes	RepeatedField<ProtoOADepthQuote>	Repeated	The list of changes in the depth of market quotes.
deletedQuotes	RepeatedField<uint64>	Repeated	The list of quotes to delete.
ProtoOAErrorRes¶
Generic response when an ERROR occurred.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Optional	The unique identifier of the trader's account in cTrader platform.
errorCode	string	Required	The name of the ProtoErrorCode or the other custom ErrorCodes (e.g. ProtoCHErrorCode).
description	string	Optional	The error description.
maintenanceEndTimestamp	int64	Optional	The Unix time in seconds when the current maintenance session will be ended.
retryAfter	uint64	Optional	When you hit rate limit with errorCode=BLOCKED_PAYLOAD_TYPE, this field will contain amount of seconds until related payload type will be unlocked.
ProtoOAExecutionEvent¶
Event that is sent following the successful order acceptance or execution by the server.

Acts as response to the ProtoOANewOrderReq, ProtoOACancelOrderReq, ProtoOAAmendOrderReq, ProtoOAAmendPositionSLTPReq, ProtoOAClosePositionReq requests.

Also, the event is sent when a Deposit/Withdrawal took place.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
executionType	ProtoOAExecutionType	Required	Type of the order operation. For example: ACCEPTED, FILLED, etc.
position	ProtoOAPosition	Optional	Reference to the position linked with the execution
order	ProtoOAOrder	Optional	Reference to the initial order.
deal	ProtoOADeal	Optional	Reference to the deal (execution).
bonusDepositWithdraw	ProtoOABonusDepositWithdraw	Optional	Reference to the Bonus Deposit or Withdrawal operation.
depositWithdraw	ProtoOADepositWithdraw	Optional	Reference to the Deposit or Withdrawal operation.
errorCode	string	Optional	The name of the ProtoErrorCode or the other custom ErrorCodes (e.g. ProtoCHErrorCode).
isServerEvent	bool	Optional	If TRUE then the event generated by the server logic instead of the trader's request. (e.g. stop-out).
ProtoOAExpectedMarginReq¶
Request for getting the margin estimate according to leverage profiles.

Can be used before sending a new order request.

This doesn't consider ACCORDING_TO_GSL margin calculation type, as this calculation is trivial: usedMargin = (VWAP price of the position - GSL price) * volume * Quote2Deposit.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
symbolId	int64	Required	Unique identifier of the Symbol in cTrader platform.
volume	RepeatedField<int64>	Repeated	Volume represented in 0.01 of a unit (e.g. 1000 in protocol means 10.00 units).
ProtoOAExpectedMarginRes¶
The response to the ProtoOAExpectedMarginReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
margin	RepeatedField<ProtoOAExpectedMargin>	Repeated	The buy and sell margin estimate.
moneyDigits	uint32	Optional	Specifies the exponent of the monetary values. E.g. moneyDigits = 8 must be interpret as business value multiplied by 10^8, then real balance would be 10053099944 / 10^8 = 100.53099944. Affects margin.buyMargin, margin.sellMargin.
ProtoOAGetAccountListByAccessTokenReq¶
Request for getting the list of granted trader's account for the access token.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
accessToken	string	Required	The Access Token issued for providing access to the Trader's Account.
ProtoOAGetAccountListByAccessTokenRes¶
Response to the ProtoOAGetAccountListByAccessTokenReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
accessToken	string	Required	The Access Token issued for providing access to the Trader's Account.
permissionScope	ProtoOAClientPermissionScope	Optional	SCOPE_VIEW, SCOPE_TRADE.
ctidTraderAccount	RepeatedField<ProtoOACtidTraderAccount>	Repeated	The list of the accounts.
ProtoOAGetCtidProfileByTokenReq¶
Request for getting details of Trader's profile.

Limited due to GDRP requirements.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
accessToken	string	Required	The Access Token issued for providing access to the Trader's Account.
ProtoOAGetCtidProfileByTokenRes¶
Response to the ProtoOAGetCtidProfileByTokenReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
profile	ProtoOACtidProfile	Required	Trader's profile.
ProtoOAGetDynamicLeverageByIDReq¶
Request for getting a dynamic leverage entity referenced in ProtoOASymbol.

leverageId.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
leverageId	int64	Required	
ProtoOAGetDynamicLeverageByIDRes¶
Response to the ProtoOAGetDynamicLeverageByIDReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
leverage	ProtoOADynamicLeverage	Required	
ProtoOAGetPositionUnrealizedPnLReq¶
Request for getting trader's positions' unrealized PnLs.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	The unique identifier of the trader's account in cTrader platform.
ProtoOAGetPositionUnrealizedPnLRes¶
Response to ProtoOAGetPositionUnrealizedPnLReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	The unique identifier of the trader's account in cTrader platform.
positionUnrealizedPnL	RepeatedField<ProtoOAPositionUnrealizedPnL>	Repeated	Information about trader's positions' unrealized PnLs.
moneyDigits	uint32	Required	Specifies the exponent of various monetary values. E.g., moneyDigits = 8 should be interpreted as the value multiplied by 10^8 with the 'real' value equal to 10053099944 / 10^8 = 100.53099944. Affects positionUnrealizedPnL.grossUnrealizedPnL, positionUnrealizedPnL.netUnrealizedPnL.
ProtoOAGetTickDataReq¶
Request for getting historical tick data for the symbol.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
symbolId	int64	Required	Unique identifier of the Symbol in cTrader platform.
type	ProtoOAQuoteType	Required	Bid/Ask (½).
fromTimestamp	int64	Optional	The Unix time in milliseconds of starting the search. Must be bigger or equal to zero (1st Jan 1970).
toTimestamp	int64	Optional	The Unix time in milliseconds of finishing the search. <= 2147483646000 (19th Jan 2038).
ProtoOAGetTickDataRes¶
Response to the ProtoOAGetTickDataReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
tickData	RepeatedField<ProtoOATickData>	Repeated	The list of ticks is in chronological order (newest first). The first tick contains Unix time in milliseconds while all subsequent ticks have the time difference in milliseconds between the previous and the current one.
hasMore	bool	Required	If TRUE then the number of records by filter is larger than chunkSize, the response contains the number of records that is equal to chunkSize.
ProtoOAGetTrendbarsReq¶
Request for getting historical trend bars for the symbol.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
fromTimestamp	int64	Optional	The Unix time in milliseconds from which the search starts. Must be bigger or equal to zero (1st Jan 1970).
toTimestamp	int64	Optional	The Unix time in milliseconds of finishing the search. Smaller or equal to 2147483646000 (19th Jan 2038).
period	ProtoOATrendbarPeriod	Required	Specifies period of trend bar series (e.g. M1, M10, etc.).
symbolId	int64	Required	Unique identifier of the Symbol in cTrader platform.
count	uint32	Optional	Limit number of trend bars in response back from toTimestamp.
ProtoOAGetTrendbarsRes¶
Response to the ProtoOAGetTrendbarsReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
period	ProtoOATrendbarPeriod	Required	Specifies period of trend bar series (e.g. M1, M10, etc.).
timestamp	int64	Optional	Simply don't use this field, as your original request already contains toTimestamp.
trendbar	RepeatedField<ProtoOATrendbar>	Repeated	The list of trend bars.
symbolId	int64	Optional	Unique identifier of the Symbol in cTrader platform.
hasMore	bool	Optional	If TRUE then the number of records by filter is larger than chunkSize, the response contains the number of records that is equal to chunkSize.
ProtoOAMarginCallListReq¶
Request for a list of existing margin call thresholds configured for a user.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	
ProtoOAMarginCallListRes¶
Response with a list of existing user Margin Calls, usually contains 3 items.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
marginCall	RepeatedField<ProtoOAMarginCall>	Repeated	
ProtoOAMarginCallTriggerEvent¶
Event that is sent when account margin level reaches target marginLevelThreshold.

Event is sent no more than once every 10 minutes to avoid spamming.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	
marginCall	ProtoOAMarginCall	Required	
ProtoOAMarginCallUpdateEvent¶
Event that is sent when a Margin Call threshold configuration is updated.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	
marginCall	ProtoOAMarginCall	Required	
ProtoOAMarginCallUpdateReq¶
Request to modify marginLevelThreshold of specified marginCallType for ctidTraderAccountId.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	
marginCall	ProtoOAMarginCall	Required	
ProtoOAMarginCallUpdateRes¶
If this response received, it means that margin call was successfully updated.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ProtoOAMarginChangedEvent¶
Event that is sent when the margin allocated to a specific position is changed.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
positionId	uint64	Required	The unique ID of the position.
usedMargin	uint64	Required	The new value of the margin used.
moneyDigits	uint32	Optional	Specifies the exponent of the monetary values. E.g. moneyDigits = 8 must be interpret as business value multiplied by 10^8, then real balance would be 10053099944 / 10^8 = 100.53099944. Affects usedMargin.
ProtoOANewOrderReq¶
Request for sending a new trading order.

Allowed only if the accessToken has the "trade" permissions for the trading account.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	The unique identifier of the trader's account in cTrader platform.
symbolId	int64	Required	The unique identifier of a symbol in cTrader platform.
orderType	ProtoOAOrderType	Required	The type of an order - MARKET, LIMIT, STOP, MARKET_RANGE, STOP_LIMIT.
tradeSide	ProtoOATradeSide	Required	The trade direction - BUY or SELL.
volume	int64	Required	The volume represented in 0.01 of a unit (e.g. 1000 in protocol means 10.00 units).
limitPrice	double	Optional	The limit price, can be specified for the LIMIT order only.
stopPrice	double	Optional	Stop Price, can be specified for the STOP and the STOP_LIMIT orders only.
timeInForce	ProtoOATimeInForce	Optional	The specific order execution or expiration instruction - GOOD_TILL_DATE, GOOD_TILL_CANCEL, IMMEDIATE_OR_CANCEL, FILL_OR_KILL, MARKET_ON_OPEN.
expirationTimestamp	int64	Optional	The Unix time in milliseconds of Order expiration. Should be set for the Good Till Date orders.
stopLoss	double	Optional	The absolute Stop Loss price (1.23456 for example). Not supported for MARKET orders.
takeProfit	double	Optional	The absolute Take Profit price (1.23456 for example). Unsupported for MARKET orders.
comment	string	Optional	User-specified comment. MaxLength = 512.
baseSlippagePrice	double	Optional	Base price to calculate relative slippage price for MARKET_RANGE order.
slippageInPoints	int32	Optional	Slippage distance for MARKET_RANGE and STOP_LIMIT order.
label	string	Optional	User-specified label. MaxLength = 100.
positionId	int64	Optional	Reference to the existing position if the Order is intended to modify it.
clientOrderId	string	Optional	Optional user-specific clientOrderId (similar to FIX ClOrderID). MaxLength = 50.
relativeStopLoss	int64	Optional	Relative Stop Loss that can be specified instead of the absolute as one. Specified in 1/100000 of unit of a price. (e.g. 123000 in protocol means 1.23, 53423782 means 534.23782) For BUY stopLoss = entryPrice - relativeStopLoss, for SELL stopLoss = entryPrice + relativeStopLoss.
relativeTakeProfit	int64	Optional	Relative Take Profit that can be specified instead of the absolute one. Specified in 1/100000 of unit of a price. (e.g. 123000 in protocol means 1.23, 53423782 means 534.23782) For BUY takeProfit = entryPrice + relativeTakeProfit, for SELL takeProfit = entryPrice - relativeTakeProfit.
guaranteedStopLoss	bool	Optional	If TRUE then stopLoss is guaranteed. Required to be set to TRUE for the Limited Risk accounts (ProtoOATrader.isLimitedRisk=true).
trailingStopLoss	bool	Optional	If TRUE then the Stop Loss is Trailing.
stopTriggerMethod	ProtoOAOrderTriggerMethod	Optional	Trigger method for the STOP or the STOP_LIMIT pending order.
ProtoOAOrderDetailsReq¶
Request for getting Order and its related Deals.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
orderId	int64	Required	The unique ID of the Order.
ProtoOAOrderDetailsRes¶
Response to the ProtoOAOrderDetailsReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
order	ProtoOAOrder	Required	Order details.
deal	RepeatedField<ProtoOADeal>	Repeated	All Deals created by filling the specified Order.
ProtoOAOrderErrorEvent¶
Event that is sent when errors occur during the order requests.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
errorCode	string	Required	The name of the ProtoErrorCode or the other custom ErrorCodes (e.g. ProtoCHErrorCode).
orderId	int64	Optional	The unique ID of the order.
positionId	int64	Optional	The unique ID of the position.
description	string	Optional	The error description.
ProtoOAOrderListByPositionIdReq¶
Request for retrieving Orders related to a Position by using Position ID.

Filtered by utcLastUpdateTimestamp.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
positionId	int64	Required	The unique ID of the Position.
fromTimestamp	int64	Optional	The Unix time from which the search starts >=0 (1st Jan 1970). Search by utcLastUpdateTimestamp of the Order.
toTimestamp	int64	Optional	The Unix time where to stop searching <= 2147483646000 (19th Jan 2038). Search by utcLastUpdateTimestamp of the Order.
ProtoOAOrderListByPositionIdRes¶
Response to ProtoOAOrderListByPositionIdReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
order	RepeatedField<ProtoOAOrder>	Repeated	Orders related to the specified Position, sorted by utcLastUpdateTimestamp in descending order (newest first).
hasMore	bool	Required	If TRUE then the number of records by filter is larger than chunkSize, the response contains the number of records that is equal to chunkSize.
ProtoOAOrderListReq¶
Request for getting Trader's orders filtered by timestamp

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
fromTimestamp	int64	Optional	The Unix time from which the search starts >=0 (1st Jan 1970).
toTimestamp	int64	Optional	The Unix time where to stop searching <= 2147483646000 (19th Jan 2038).
ProtoOAOrderListRes¶
The response to the ProtoOAOrderListReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
order	RepeatedField<ProtoOAOrder>	Repeated	The list of the orders.
hasMore	bool	Required	If TRUE then the number of records by filter is larger than chunkSize, the response contains the number of records that is equal to chunkSize.
ProtoOAReconcileReq¶
Request for getting Trader's current open positions and pending orders data.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
returnProtectionOrders	bool	Optional	If TRUE, then current protection orders are returned separately, otherwise you can use position.stopLoss and position.takeProfit fields.
ProtoOAReconcileRes¶
The response to the ProtoOAReconcileReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
position	RepeatedField<ProtoOAPosition>	Repeated	The list of trader's account open positions.
order	RepeatedField<ProtoOAOrder>	Repeated	The list of trader's account pending orders.
ProtoOARefreshTokenReq¶
Request to refresh the access token using refresh token of granted trader's account.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
refreshToken	string	Required	The Refresh Token issued for updating Access Token.
ProtoOARefreshTokenRes¶
Response to the ProtoOARefreshTokenReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
accessToken	string	Required	The Access Token issued for providing access to the Trader's Account.
tokenType	string	Required	bearer
expiresIn	int64	Required	Access Token expiration in seconds.
refreshToken	string	Required	Your new Refresh Token.
ProtoOASpotEvent¶
Event that is sent when a new spot event is generated on the server side.

Requires subscription on the spot events, see ProtoOASubscribeSpotsReq.

First event, received after subscription will contain latest spot prices even if market is closed.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
symbolId	int64	Required	Unique identifier of the Symbol in cTrader platform.
bid	uint64	Optional	Bid price. Specified in 1/100000 of unit of a price. (e.g. 123000 in protocol means 1.23, 53423782 means 534.23782)
ask	uint64	Optional	Ask price. Specified in 1/100000 of unit of a price. (e.g. 123000 in protocol means 1.23, 53423782 means 534.23782)
trendbar	RepeatedField<ProtoOATrendbar>	Repeated	Returns live trend bar. Requires subscription on the trend bars.
sessionClose	uint64	Optional	Last session close. Specified in 1/100000 of unit of a price. (e.g. 123000 in protocol means 1.23, 53423782 means 534.23782)
timestamp	int64	Optional	The Unix time for spot.
ProtoOASubscribeDepthQuotesReq¶
Request for subscribing on depth of market of the specified symbol.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
symbolId	RepeatedField<int64>	Repeated	Unique identifier of the Symbol in cTrader platform.
ProtoOASubscribeDepthQuotesRes¶
Response to the ProtoOASubscribeDepthQuotesReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
ProtoOASubscribeLiveTrendbarReq¶
Request for subscribing for live trend bars.

Requires subscription on the spot events, see ProtoOASubscribeSpotsReq.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
period	ProtoOATrendbarPeriod	Required	Specifies period of trend bar series (e.g. M1, M10, etc.).
symbolId	int64	Required	Unique identifier of the Symbol in cTrader platform.
ProtoOASubscribeLiveTrendbarRes¶
Response to the ProtoOASubscribeLiveTrendbarReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
ProtoOASubscribeSpotsReq¶
Request for subscribing on spot events of the specified symbol.

After successful subscription you'll receive technical ProtoOASpotEvent with latest price, after which you'll start receiving updates on prices via consequent ProtoOASpotEvents.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
symbolId	RepeatedField<int64>	Repeated	Unique identifier of the Symbol in cTrader platform.
subscribeToSpotTimestamp	bool	Optional	If TRUE you will also receive the timestamp in ProtoOASpotEvent.
ProtoOASubscribeSpotsRes¶
Response to the ProtoOASubscribeSpotsReq request.

Reflects that your request to subscribe for symbol has been added to queue.

You'll receive technical ProtoOASpotEvent with current price shortly after this response.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
ProtoOASymbolByIdReq¶
Request for getting a full symbol entity.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
symbolId	RepeatedField<int64>	Repeated	Unique identifier of the symbol in cTrader platform.
ProtoOASymbolByIdRes¶
Response to the ProtoOASymbolByIdReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
symbol	RepeatedField<ProtoOASymbol>	Repeated	Symbol entity with the full set of fields.
archivedSymbol	RepeatedField<ProtoOAArchivedSymbol>	Repeated	Archived symbols.
ProtoOASymbolCategoryListReq¶
Request for a list of symbol categories available for a trading account.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
ProtoOASymbolCategoryListRes¶
Response to the ProtoSymbolCategoryListReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
symbolCategory	RepeatedField<ProtoOASymbolCategory>	Repeated	The list of symbol categories.
ProtoOASymbolChangedEvent¶
Event that is sent when the symbol is changed on the Server side.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
symbolId	RepeatedField<int64>	Repeated	Unique identifier of the Symbol in cTrader platform.
ProtoOASymbolsForConversionReq¶
Request for getting a conversion chain between two assets that consists of several symbols.

Use when no direct quote is available.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
firstAssetId	int64	Required	The ID of the firs asset in the conversation chain. e.g.: for EUR/USD the firstAssetId is EUR ID and lastAssetId is USD ID.
lastAssetId	int64	Required	The ID of the last asset in the conversation chain. e.g.: for EUR/USD the firstAssetId is EUR ID and lastAssetId is USD ID.
ProtoOASymbolsForConversionRes¶
Response to the ProtoOASymbolsForConversionReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
symbol	RepeatedField<ProtoOALightSymbol>	Repeated	Conversion chain of the symbols (e.g. EUR/USD, USD/JPY, GBP/JPY -> EUR/GBP).
ProtoOASymbolsListReq¶
Request for a list of symbols available for a trading account.

Symbol entries are returned with the limited set of fields.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
includeArchivedSymbols	bool	Optional	Whether to include old archived symbols into response.
ProtoOASymbolsListRes¶
Response to the ProtoOASymbolsListReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
symbol	RepeatedField<ProtoOALightSymbol>	Repeated	The list of symbols.
archivedSymbol	RepeatedField<ProtoOAArchivedSymbol>	Repeated	The list of archived symbols.
ProtoOATraderReq¶
Request for getting data of Trader's Account.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
ProtoOATraderRes¶
Response to the ProtoOATraderReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
trader	ProtoOATrader	Required	The Trader account information.
ProtoOATraderUpdatedEvent¶
Event that is sent when a Trader is updated on Server side.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
trader	ProtoOATrader	Required	The Trader account information.
ProtoOATrailingSLChangedEvent¶
Event that is sent when the level of the Trailing Stop Loss is changed due to the price level changes.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
positionId	int64	Required	The unique ID of the position.
orderId	int64	Required	The unique ID of the order.
stopPrice	double	Required	New value of the Stop Loss price.
utcLastUpdateTimestamp	int64	Required	The Unix time in milliseconds when the Stop Loss was updated.
ProtoOAUnsubscribeDepthQuotesReq¶
Request for unsubscribing from the depth of market of the specified symbol.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
symbolId	RepeatedField<int64>	Repeated	Unique identifier of the Symbol in cTrader platform.
ProtoOAUnsubscribeDepthQuotesRes¶
Response to the ProtoOAUnsubscribeDepthQuotesReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
ProtoOAUnsubscribeLiveTrendbarReq¶
Request for unsubscribing from the live trend bars.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
period	ProtoOATrendbarPeriod	Required	Specifies period of trend bar series (e.g. M1, M10, etc.).
symbolId	int64	Required	Unique identifier of the Symbol in cTrader platform.
ProtoOAUnsubscribeLiveTrendbarRes¶
Response to the ProtoOASubscribeLiveTrendbarReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
ProtoOAUnsubscribeSpotsReq¶
Request for unsubscribing from the spot events of the specified symbol.

Request to stop receiving ProtoOASpotEvents related to particular symbols.

Unsubscription is useful to minimize traffic, especially during high volatility events.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
symbolId	RepeatedField<int64>	Repeated	Unique identifier of the Symbol in cTrader platform.
ProtoOAUnsubscribeSpotsRes¶
Response to the ProtoOASubscribeSpotsRes request.

Reflects that your request to unsubscribe will has been added to queue and will be completed shortly.

You may still occasionally receive ProtoOASpotEvents until request processing is complete.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ctidTraderAccountId	int64	Required	Unique identifier of the trader's account. Used to match responses to trader's accounts.
ProtoOAVersionReq¶
Request for getting the proxy version.

Can be used to check the current version of the Open API scheme.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
ProtoOAVersionRes¶
Response to the ProtoOAVersionReq request.

Field	Type	Label	Description
payloadType	ProtoOAPayloadType	Optional	
version	string	Required	The current version of the server application.


8. .NET SDK¶
If you decide to integrate with the cTrader Open API using any of the .NET programming languages, our official .NET SDK is here to help.

What the .NET SDK Does¶
The .NET SDK contains a variety of helpful classes, methods, and solutions which, following their implementation, should allow you to focus on making your service better rather than having to create custom systems for establishing a TCP/WebSocket connection or sending/receiving Protobuf messages.

Installation¶
Open the NuGet package manager console and run the following command.

Install-Package cTrader.OpenAPI.Net
Alternatively, you can search for the cTrader.OpenAPI.NET package when working with the NuGet package manager solution.

The .NET SDK in GitHub

To view the GitHub repository for the .NET SDK, click here. If you want to suggest an improvement, simply fork the repo and open a pull request.

To view several samples of applications created via the .NET SDK, click here. You are free to reuse code from these samples in your own applications.


9. Terms of Use¶
You can find the terms of use of cTrader Open API here.

To start using the API, just apply for your own Partner's Credentials (OAuth Public Client ID and Client Secret).

For more details check the Open Authentication section of this guide.

Acceptance of Terms of Use¶
By registering an application and by using cTrader Open API, you confirm that you have read, understood and agree to these terms of use.

API License¶
As long as you adhere to the terms of use, we grant you a limited, non-exclusive, non-assignable, non-transferable license under Spotware’s intellectual property rights to use the APIs to develop, test, and support your Application, and to let your customers use your integration of the APIs within your Application.

Cost¶
cTrader Open API is offered for free. Nevertheless, Spotware Systems Ltd reserves the right to change the pricing policy without prior notice and without your consent.

Limitation of Liability¶
The API is provided “as is”. It is your sole responsibility to test the API and decide if it is appropriate for your business needs.

Spotware Systems Ltd does not make any promises nor does it provide any guarantee regarding the performance, reliability and availability of the API.

In no event shall Spotware Systems Ltd be liable for any damages (including, without limitation, lost profits, business interruption, or lost information) arising out of use of or inability to use the API, even if Spotware Systems Ltd has been advised of the possibility of such damages.

In no event will Spotware Systems Ltd be liable for loss of data or for indirect, special, incidental, consequential (including lost profit), or other damages based on contract, tort or otherwise.

Spotware Systems Ltd shall have no liability with respect to the content of Spotware Systems products or any part thereof, including but not limited to errors or omissions contained therein, libel, infringements of rights of publicity, privacy, trademark rights, business interruption, personal injury, loss of privacy, moral rights or the disclosure of confidential information.

Modification¶
Spotware Systems Ltd reserves the right to modify the API and the terms of use at any time without prior notice and without any liability.

Fair Use¶
Resources¶
You agree to use the API and the resources provided by Spotware Systems Ltd in a fair and sensible manner.

You should take all the measures required on your side to avoid unreasonable use of APIs resources.

In case of misuse of the API, Spotware Systems Ltd reserves the right to restrict or remove access to your application.

User Data¶
By using the API you can gain access to sensitive user information. You may not use, store, distribute or process traders’ personal information in any way other than to fulfill the specific trading objectives which your application has been built to serve.

In addition, any processing of traders’ personal information must have the explicit prior approval from the traders and a valid legal basis for the intended processing.

Finally, you should not provide or embed in the application functionality that results in the execution of trading actions on behalf of the trader, without his / her explicit prior approval.

Also by using cTrader Open API, you acknowledge that you operate in accordance with General Data Protection Regulation (GDPR) (EU) 2016/679.

Spotware reserves the right to restrict or remove access to applications which are found to be in breach of GDPR and privacy-specific obligations and terms.

We will delete your cTrader Open API application(s) if we delete your cTrader ID user account as per GDPR, because your application may contain your personal data like your name or phone number.

Use of Application Contact Details¶
As part of the use of the API, Spotware is required to have limited personal contact details of designated personnel of the developer and / or his team, comprising first and last names, the person’s employer’s name, email address and a telephone number. These mandatory details are a condition of using the Open API and shall be made available in the cBroker platform to Brokers (not traders) for the purposes of requesting support, if necessary.

The personal data shall be retained for as long as the cTrader Open API is used by the application, and shall be removed after a maximum of 6 months following termination of such use.

Publicity¶
Spotware Systems Ltd reserves the right to refer to you as a user of cTrader Open API.