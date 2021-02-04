#!/usr/bin/env python

import sys; sys.path.insert(0, 'lib') # this line is necessary for the rest
import os                             # of the imports to work!

import web
import sqlitedb
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

###########################################################################################
##########################DO NOT CHANGE ANYTHING ABOVE THIS LINE!##########################
###########################################################################################

######################BEGIN HELPER METHODS######################

# helper method to convert times from database (which will return a string)
# into datetime objects. This will allow you to compare times correctly (using
# ==, !=, <, >, etc.) instead of lexicographically as strings.

# Sample use:
# current_time = string_to_time(sqlitedb.getTime())

def string_to_time(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')

# helper method to render a template in the templates/ directory
#
# `template_name': name of template file to render
#
# `**context': a dictionary of variable names mapped to values
# that is passed to Jinja2's templating engine
#
# See curr_time's `GET' method for sample usage
#
# WARNING: DO NOT CHANGE THIS METHOD
def render_template(template_name, **context):
    extensions = context.pop('extensions', [])
    globals = context.pop('globals', {})

    jinja_env = Environment(autoescape=True,
            loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')),
            extensions=extensions,
            )
    jinja_env.globals.update(globals)

    web.header('Content-Type','text/html; charset=utf-8', unique=True)

    return jinja_env.get_template(template_name).render(context)

#####################END HELPER METHODS#####################

#first parameter => URL, second parameter => class name
urls = ('/currtime', 'curr_time',
        '/selecttime', 'select_time',
        '/search', 'search_auction',
        '/items', 'item_status',
        '/add_bid', 'place_bid',
        '/appbase', 'appbase',
        )

class curr_time:
    # A simple GET request, to '/currtime'
    #
    # Notice that we pass in `current_time' to our `render_template' call
    # in order to have its value displayed on the web page
    def GET(self):
        current_time = sqlitedb.getTime()
        return render_template('curr_time.html', time = current_time)

class select_time:
    # Aanother GET request, this time to the URL '/selecttime'
    def GET(self):
        return render_template('select_time.html')

    # A POST request
    #
    # You can fetch the parameters passed to the URL
    # by calling `web.input()' for **both** POST requests
    # and GET requests
    def POST(self):
        post_params = web.input()
        MM = post_params['MM']
        dd = post_params['dd']
        yyyy = post_params['yyyy']
        HH = post_params['HH']
        mm = post_params['mm']
        ss = post_params['ss']
        enter_name = post_params['entername']

        selected_time = '%s-%s-%s %s:%s:%s' % (yyyy, MM, dd, HH, mm, ss)
        update_message = '(Hello, %s. Previously selected time was: %s.)' % (enter_name, selected_time)
        # Save the selected time as the current time in the database
        try:
            sqlitedb.updateTime(selected_time)
        except Exception as timeExc:
            update_message = 'Cannot save selected time, it is invalid.'
            print(str(timeExc))
        # Here, we assign `update_message' to `message', which means
        # we'll refer to it in our template as `message'
        return render_template('select_time.html', message = update_message)

class search_auction:
    #Get request to URL '/search'
    def GET(self):
        return render_template('search.html')

    #POST request
    def POST(self):
        #get user input
        post_params = web.input()
        userID = post_params['userID']
        itemID = post_params['itemID']
        category = post_params['category']
        description = post_params['description']
        minPrice = post_params['minPrice']
        maxPrice = post_params['maxPrice']
        status = post_params['status']

        #error check if user actually inputted stuff in
        if userID == '' and itemID == '' and category == '' and description == '' and minPrice == '' and maxPrice == '':
            return render_template('search.html', message = 'All of the queries are missing a value. Please try again.')
        else:
            #search the database based on the user input, and return the results to search.html
            val = sqlitedb.searchAuction(userID,itemID,category,description,minPrice,maxPrice,status)
            return render_template('search.html', search_result = val)

class item_status:
    #Get request to URL '/items'
    def GET(self):
        #get the user's input on a specific item ID.
        post_params = web.input()
        itemID = post_params['id']

        #retrieve status and bidding information for the specific itemID
        item = sqlitedb.getItemById(itemID)
        categories = sqlitedb.getCategoryById(itemID)
        bids = sqlitedb.getBidById(itemID)

        #initialize items to not yet ended and no buy price, and therefore, no winner
        ended = False
        hasBuyPrice = False
        winner = ""
        buyPrice = ""

        #check and update the status of the auction
        if item.Started <= sqlitedb.getTime() and item.Ends >= sqlitedb.getTime():
            status = 'Still open'
        elif item.Started > sqlitedb.getTime():
            status = 'Not yet started'
        else:
            #at this point, item's end time is already after current time
            status = 'Ended'

        #get a winner if one exists
        if item.Number_of_Bids == 0:
            noBids = True
        else:
            noBids = False
            winner = sqlitedb.getWinnerById(itemID).UserID

        #if bid price is higher than buy price, then close the auction
        if item.Buy_Price is not None:
            hasBuyPrice = True
            buyPrice = item.Buy_Price
            if status == 'Ended' or float(item.Currently) >= float(item.Buy_Price):
                status = 'Ended'
                ended = True
        elif status == 'Ended':
            ended = True

        return render_template('items.html', id = itemID, bids = bids, Name = item.Name, Category = categories.Category, Ends = item.Ends, Started = item.Started, Number_of_Bids = item.Number_of_Bids, Seller = item.Seller_UserID, Description = item.Description, Currently = item.Currently, noBids = noBids, ended = ended, Status = status, Winner = winner, buyPrice = buyPrice, hasBuyPrice = hasBuyPrice)

class place_bid:
    #Get request to URL '/add_bid'
    def GET(self):
        return render_template('add_bid.html')

    #POST request
    def POST(self):
        #get user input on userID, itemID, and bid amount
        post_params = web.input()
        userID = post_params['userID']
        itemID = post_params['itemID']
        Amount = post_params['price']

        #error check if all values were input
        if userID == '' or itemID == '' or Amount == '':
            return render_template('add_bid.html', message = 'At least one of the following is invalid: UserID, ItemID, or Amount.')
        else:
            #if all values present, retrieve the specified users and items if possible
            curr_user = sqlitedb.getUserById(userID)
            curr_item = sqlitedb.getItemById(itemID)
        
        #if the specified user doesn't exist:
        if curr_user is None:
            return render_template('add_bid.html', message = 'Could not find user with UserID.')
        #if the specified user is the item's seller:
        elif curr_user.UserID == curr_item.Seller_UserID:
            return render_template('add_bid.html', message = 'UserID is the ID of the seller, cannot bid.')
        #if the specified item doesn't exist:
        elif curr_item is None:
            return render_template('add_bid.html', message = 'Could not find item with ItemID.')
        #if the specified amount is negative:
        elif float(Amount) < 0:
            return render_template('add_bid.html', message = 'The specified amount is negative.')
        #if the specified amount is less than the currently highest bid price:
        elif float(Amount) <= float(curr_item.First_Bid) or float(Amount) <= float(curr_item.Currently):
            return render_template('add_bid.html', message = 'The specified amount is too small.')
        #if the specified auction has not yet started:
        elif string_to_time(sqlitedb.getTime()) < string_to_time(curr_item.Started):
            return render_template('add_bid.html', message = 'The auction has not yet started.')
        #if the specified auction has already ended:
        elif string_to_time(sqlitedb.getTime()) >= string_to_time(curr_item.Ends):
            return render_template('add_bid.html', message = 'The auction has already ended.')

        #If the auction has a specified buy price:
        if curr_item.Buy_Price is not None:
            #if specified amount is greater than or equal to buy price:
            if float(Amount) >= float(curr_item.Buy_Price):
                #indicate that the auction has been purchased, and close the auction (IF SUCCESSFUL).
                #On the website, if the Result specifies "not successful", then this step has not been successful due to constraints.
                successful_purchase = 'You have purchased item: %s for: %s. NOTE: Check Result below to see if it was successful.' % (curr_item.Name, Amount)
                return render_template('add_bid.html', message = successful_purchase, add_result = sqlitedb.newBid(userID, itemID, Amount))

        #place a new bid on the item with the specified amount
        successful_bid = 'You have placed a bid on item: %s for: %s. NOTE: Check Result below to see if it was successful.' % (curr_item.Name, Amount)
        return render_template('add_bid.html', message = successful_bid, add_result = sqlitedb.newBid(userID, itemID, Amount))

###########################################################################################
##########################DO NOT CHANGE ANYTHING BELOW THIS LINE!##########################
###########################################################################################

if __name__ == '__main__':
    web.internalerror = web.debugerror
    app = web.application(urls, globals())
    app.add_processor(web.loadhook(sqlitedb.enforceForeignKey))
    app.run()
