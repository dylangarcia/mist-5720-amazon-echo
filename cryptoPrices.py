"""
This sample demonstrates a simple skill built with the Amazon Alexa Skills Kit.
The Intent Schema, Custom Slots, and Sample Utterances for this skill, as well
as testing instructions are located at http://amzn.to/1LzFrj6

For additional samples, visit the Alexa Skills Kit Getting Started guide at
http://amzn.to/1LGWsLG
"""

import urllib.request
import json

# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': title,
            'content': output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------


def get_balance(session):
    return round(session.get("attributes", {}).get("balance", 0), 2)


def get_welcome_response(intent, session):
    session_attributes, card_title, should_end_session = {}, "Welcome!", False
    portfolio_price = get_price_of_portfolio(intent, session)
    balance = 50000
    session_attributes["balance"] = balance
    speech_output = "Welcome to your Crypto Portfolio. " \
                    "Your portfolio is worth ${}. " \
                    "You have a balance of ${}.".format(portfolio_price, balance)
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Thank you for interaction with your Crypto Portfolio."
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def get_required_data(intent, session):
    session_attributes = session.get("attributes", {})
    card_title = (intent or {}).get("name", "Welcome!")
    should_end_session = False
    return session_attributes, card_title, should_end_session


def get_price_of_ticker(ticker):
    req = urllib.request.Request("https://api.coinmarketcap.com/v1/ticker/{}/".format(ticker))
    with urllib.request.urlopen(req) as open_req:
        response = json.loads(open_req.read().decode("utf-8"))
    price = float(response[0]["price_usd"])
    price = round(price, 2)
    return price


def get_price_of_portfolio(intent, session, portfolio=None):
    session_attributes, card_title, should_end_session = get_required_data(intent, session)
    portfolio = portfolio or session_attributes.get("portfolio", [])
    portfolio_price = 0
    for entry in portfolio:
        amount = entry["amount"]
        price = get_price_of_ticker(entry["ticker"])
        portfolio_price += amount * price
    portfolio_price = round(portfolio_price, 2)
    return portfolio_price


def get_price_of_portfolio_intent(intent, session):
    session_attributes, card_title, should_end_session = get_required_data(intent, session)
    portfolio_price = get_price_of_portfolio(intent, session)
    speech_output = "The price of your portfolio is currently ${}.".format(portfolio_price)
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def get_contents_of_portfolio(intent, session):
    session_attributes, card_title, should_end_session = get_required_data(intent, session)
    portfolio = session_attributes.get("portfolio", [])
    contents = []
    for entry in portfolio:
        ticker, amount = entry["ticker"], entry["amount"]
        contents.append("{} {}".format(amount, ticker))
    return "{} and {}".format(", ".join(contents[:-1]), contents[-1])


def get_contents_of_portfolio_intent(intent, session):
    session_attributes, card_title, should_end_session = get_required_data(intent, session)
    portfolio_contents = get_contents_of_portfolio(intent, session)
    speech_output = "You are currently holding {} in your portfolio.".format(portfolio_contents)
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def change_balance(intent, session, amount, delta):
    return get_balance(session) + (amount * delta)


def add_to_portfolio(intent, session):
    session_attributes, card_title, should_end_session = get_required_data(intent, session)
    ticker = intent["slots"]["Ticker"]["value"]
    amount = int(intent["slots"]["Number"]["value"])
    price = get_price_of_ticker(ticker)
    portfolio = session_attributes.get("portfolio", [])
    current_balance = get_balance(session)
    tickers = (entry["ticker"] for entry in portfolio)
    if price * amount > current_balance:
        raise ValueError("Your balance cannot cover this purchase.") 
    if ticker in tickers:
        for entry in portfolio:
            if entry["ticker"] == ticker:
                entry["amount"] += amount
    else:
        portfolio.append(
                { 
                    "ticker": ticker,
                    "amount": amount
                }
        )
    session_attributes["balance"] = change_balance(intent, session, price * amount, -1)
    return portfolio, ticker, amount


def add_to_portfolio_intent(intent, session):
    session_attributes, card_title, should_end_session = get_required_data(intent, session)
    try:
        portfolio, ticker, amount = add_to_portfolio(intent, session)
        session_attributes["portfolio"] = portfolio
        portfolio_price = get_price_of_portfolio(intent, session, portfolio)
        session_attributes["balance"] = get_balance(session)
        balance = session_attributes["balance"]
        speech_output = ("You have added {} {} to your portfolio. " \
                         "Your portfolio is now worth ${}. " \
                         "You now have a balance of ${}.").format(amount, ticker, portfolio_price, balance)
    except Exception as e:
        speech_output = str(e)
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def remove_from_portfolio(intent, session):
    session_attributes, card_title, should_end_session = get_required_data(intent, session)
    ticker = intent["slots"]["Ticker"]["value"]
    try:
        amount = int(intent["slots"]["Number"]["value"])
    except Exception as e:
        amount = "all of your"
    portfolio = session_attributes.get("portfolio", [])
    if ticker in (entry["ticker"] for entry in portfolio):
        for entry in portfolio:
            if entry["ticker"] == ticker:
                if amount == "all of your":
                    amount = entry["amount"]
                    entry["amount"] = 0
                    break
                if entry["amount"] < amount:
                    raise ValueError("You only have {} {} in your portfolio.".format(entry["amount"], ticker))
                entry["amount"] -= amount
    else:
        raise Exception("You do not have any {} in your portfolio.".format(ticker))
    price = get_price_of_ticker(ticker)
    session_attributes["balance"] = change_balance(intent, session, price * amount, 1)
    return portfolio, ticker, amount


def remove_from_portfolio_intent(intent, session):
    session_attributes, card_title, should_end_session = get_required_data(intent, session)
    try:
        portfolio, ticker, amount = remove_from_portfolio(intent, session)
        session_attributes["portfolio"] = portfolio
        portfolio_price = get_price_of_portfolio(intent, session, portfolio)
        session_attributes["balance"] = get_balance(session)
        balance = session_attributes["balance"]
        speech_output = ("You have removed {} {} from your portfolio. " \
                         "Your portfolio is now worth ${}. " \
                         "You now have a balance of ${}.").format(amount, ticker, portfolio_price, balance)
    except Exception as e:
        speech_output = str(e)
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def get_price_of_ticker_intent(intent, session):
    session_attributes, card_title, should_end_session = get_required_data(intent, session)
    if 'ER_SUCCESS_MATCH' in intent["slots"]["Ticker"]["resolutions"]["resolutionsPerAuthority"][0]["status"]["code"]:
        ticker = intent['slots']['Ticker']['value']
        possible_choices = intent["slots"]["Ticker"]["resolutions"]["resolutionsPerAuthority"][0]["values"]
        speech_output = "You are asking about the {} coin.".format(ticker)
        # speech_output = "There are {} possible choices for the {} coin.".format(len(possible_choices), ticker)
        price = get_price_of_ticker(ticker)
        speech_output = "The price of {} is currently ${}.".format(ticker, price)
    else:
        speech_output = "I'm not sure what coin you are looking for."
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def get_current_balance_intent(intent, session):
    session_attributes, card_title, should_end_session = get_required_data(intent, session)
    balance = get_balance(session)
    speech_output = "You have a current balance of ${}.".format(balance)
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, None, should_end_session))
    

# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response(None, session)


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent_name == "GetPriceIntent":
        return get_price_of_ticker_intent(intent, session)
    elif intent_name == "AddToPortfolioIntent":
        return add_to_portfolio_intent(intent, session)
    elif intent_name == "RemoveFromPortfolioIntent":
        return remove_from_portfolio_intent(intent, session)
    elif intent_name == "GetPriceOfPortfolioIntent":
        return get_price_of_portfolio_intent(intent, session)
    elif intent_name == "GetCurrentBalanceIntent":
        return get_current_balance_intent(intent, session)
    elif intent_name == "GetContentsOfPortfolioIntent":
        return get_contents_of_portfolio_intent(intent, session)
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response(None, session)
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here


# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.[unique-value-here]"):
    #     raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])
