import web

db = web.database(dbn='sqlite', db = 'AuctionBase.db')

######################BEGIN HELPER METHODS######################

# Enforce foreign key constraints
# WARNING: DO NOT REMOVE THIS!
def enforceForeignKey():
    db.query('PRAGMA foreign_keys = ON')

# initiates a transaction on the database
def transaction():
    return db.transaction()
# Sample usage (in auctionbase.py):
#
# t = sqlitedb.transaction()
# try:
#     sqlitedb.query('[FIRST QUERY STATEMENT]')
#     sqlitedb.query('[SECOND QUERY STATEMENT]')
# except Exception as e:
#     t.rollback()
#     print str(e)
# else:
#     t.commit()
#
# check out http://webpy.org/cookbook/transactions for examples

# returns the current time from your database
def getTime():
    #should be the correct column names
    query_string = 'select Time from CurrentTime'
    results = query(query_string)
    return results[0].Time

# returns a single item specified by the Item's ID in the database
# Note: if the `result' list is empty (i.e. there are no items for a
# a given ID), this will throw an Exception!
def getItemById(item_id):
    # Catch the Exception in case `result' is empty
    query_string = 'select * from Items where ItemID = $itemID'
    result = query(query_string, {'itemID': item_id})
    try:
        return result[0]
    except IndexError:
        return None

# wrapper method around web.py's db.query method
# check out http://webpy.org/cookbook/query for more info
def query(query_string, vars = {}):
    return list(db.query(query_string, vars))

#####################END HELPER METHODS#####################

#additional methods:

#update the current time of AuctionBase (should conform to specified time constraints)
def updateTime(curr_time):
    #transaction() sample code provided from above
    t = transaction()
    try:
        db.update('CurrentTime', where = 'Time = $cTime', vars = {'cTime': getTime()}, Time = curr_time)
    except Exception as timeExc:
        #if there was an error in updating the time, avoid making changes, and elevate the error to auctionbase.py
        t.rollback()
        raise Exception
    else:
        t.commit()

#make a new bid on an item
def newBid(curr_user, curr_item, curr_amount):
    t = transaction()
    try:
        db.insert('Bids', userID = curr_user, itemID = curr_item, Amount = curr_amount, Time = getTime())
    except Exception as bidExc:
        #if there was an error in bidding, avoid making changes and indicate that a bid was not made
        t.rollback()
        return False
    else:
        t.commit()
        return True

#retrieve bid records on a specific item
def getBidById(item_id):
    #Get the userID, bid time, and bid price for the specified item
    query_string = 'select UserID as "User ID", Time as "Bid Time", Amount as "Bid Price" from Bids where ItemID = $itemID'
    result = query(query_string, {'itemID': item_id})
    try:
        return result
    except IndexError:
        return None

#retrieve a user by its specified userID. Can be used to check if a user exists.
def getUserById(user_id):
    query_string = 'select * from Users where UserID = $userID'
    result = query(query_string, {'userID': user_id})
    try:
        return result[0]
    except IndexError:
        return None

#retrieve the highest bid made for a specific item. Assumes that this bid is the winning bid.
def getWinnerById(item_id):
    query_string = 'select * from Bids where ItemID = $itemID and Amount = (select Max(Amount) from Bids where ItemID = $itemID)'
    result = query(query_string, {'itemID': item_id})
    try:
        return result[0]
    except IndexError:
        return None

#Get the categories for an item
def getCategoryById(item_id):
    query_string = 'select group_concat(Category,", ") as Category from Categories where ItemID = $itemID'
    result = query(query_string, {'itemID': item_id})
    try:
        return result[0]
    except IndexError:
        return None

#Search through the database to retrieve all details of corresponding auctions based on parameters
def searchAuction(userID, itemID, category, description, minPrice, maxPrice, status):
    #Disregard parameters that have not been specified
    if description is None:
        description = '%%'
    else:
        description = '%' + description + '%'
    if minPrice == '':
        minPrice = 0
    else:
        minPrice = float(minPrice)
    if maxPrice == '':
        maxPrice = 99999999999999999
    else:
        maxPrice = float(maxPrice)

    #All four statuses have a similar structure: Retrieve auctions that correspond to the specified
    #parameters such as category, itemID, userID, description, and prices. Grouped by itemID.

    #If searching for open auctions, also ensure that the startTime is before currTime, endTime is after currTime, and buyPrice has not been exceeded.
    if status == 'open':
        query_string = 'select Items.ItemID, Items.Name, Categories.category as Categories, Items.Started as "Start Time", Items.Ends as "End Time", CurrentTime.Time as "Current Time", Items.First_Bid as "First Bid", Items.Currently as "Current Price", Items.Number_of_Bids as "Number of Bids", Items.Buy_Price as "Buy Price", Items.Seller_UserID as "Seller ID", Items.Description, group_concat(category,", ") as Category from Items, Categories, CurrentTime where (Categories.ItemID = Items.ItemID) AND (IFNULL($category, "") = "" OR $category = Categories.category) AND (IFNULL($itemID, "") = "" OR $itemID = Items.ItemID) AND (IFNULL($userID, "") = "" OR $userID = Items.Seller_UserID) AND (Items.Description LIKE $description) AND (IFNULL(Items.Currently, Items.First_Bid) >= $minPrice) AND (IFNULL(Items.Currently, Items.First_Bid) <= $maxPrice) AND (Items.Started <= CurrentTime.Time AND Items.Ends >= CurrentTime.Time) AND (IFNULL(Items.Buy_Price, 0) > IFNULL(Items.Currently, Items.First_Bid)) group by Items.ItemID'
    #If searching for closed auctions, also ensure that endTime is before currTime OR that buyPrice has been exceeded.
    elif status == 'close':
        query_string = 'select Items.ItemID, Items.Name, Categories.category as Categories, Items.Started as "Start Time", Items.Ends as "End Time", CurrentTime.Time as "Current Time", Items.First_Bid as "First Bid", Items.Currently as "Current Price", Items.Number_of_Bids as "Number of Bids", Items.Buy_Price as "Buy Price", Items.Seller_UserID as "Seller ID", Items.Description, group_concat(category,", ") as Category from Items, Categories, CurrentTime where (Categories.ItemID = Items.ItemID) AND (IFNULL($category, "") = "" OR $category = Categories.category) AND (IFNULL($itemID, "") = "" OR $itemID = Items.ItemID) AND (IFNULL($userID, "") = "" OR $userID = Items.Seller_UserID) AND (Items.Description LIKE $description) AND (IFNULL(Items.Currently, Items.First_Bid) >= $minPrice) AND (IFNULL(Items.Currently, Items.First_Bid) <= $maxPrice) AND ((Items.Ends < CurrentTime.Time) OR (IFNULL(Items.Currently, Items.First_Bid) >= IFNULL(Items.Buy_Price, 999999999999999))) group by Items.ItemID'
    #If searching for auctions not yet started, ensure that the startTime is after currTime
    elif status == 'notStarted':
        query_string = 'select Items.ItemID, Items.Name, Categories.category as Categories, Items.Started as "Start Time", Items.Ends as "End Time", CurrentTime.Time as "Current Time", Items.First_Bid as "First Bid", Items.Currently as "Current Price", Items.Number_of_Bids as "Number of Bids", Items.Buy_Price as "Buy Price", Items.Seller_UserID as "Seller ID", Items.Description, group_concat(category,", ") as Category from Items, Categories, CurrentTime where (Categories.ItemID = Items.ItemID) AND (IFNULL($category, "") = "" OR $category = Categories.category) AND (IFNULL($itemID, "") = "" OR $itemID = Items.ItemID) AND (IFNULL($userID, "") = "" OR $userID = Items.Seller_UserID) AND (Items.Description LIKE $description) AND (IFNULL(Items.Currently, Items.First_Bid) >= $minPrice) AND (IFNULL(Items.Currently, Items.First_Bid) <= $maxPrice) AND (Items.Started > CurrentTime.Time) group by Items.ItemID'
    #No additional parameters specified if all auctions are searched.
    elif status == 'all':
        query_string = 'select Items.ItemID, Items.Name, Categories.category as Categories, Items.Started as "Start Time", Items.Ends as "End Time", CurrentTime.Time as "Current Time", Items.First_Bid as "First Bid", Items.Currently as "Current Price", Items.Number_of_Bids as "Number of Bids", Items.Buy_Price as "Buy Price", Items.Seller_UserID as "Seller ID", Items.Description, group_concat(category,", ") as Category from Items, Categories, CurrentTime where (Categories.ItemID = Items.ItemID) AND (IFNULL($category, "") = "" OR $category = Categories.category) AND (IFNULL($itemID, "") = "" OR $itemID = Items.ItemID) AND (IFNULL($userID, "") = "" OR $userID = Items.Seller_UserID) AND (Items.Description LIKE $description) AND (IFNULL(Items.Currently, Items.First_Bid) >= $minPrice) AND (IFNULL(Items.Currently, Items.First_Bid) <= $maxPrice) group by Items.ItemID'

    #Organize the query, and return it while catching possible errors.
    result = query(query_string, {'category': category, 'itemID': itemID, 'userID': userID, 'description': description, 'minPrice': minPrice, 'maxPrice': maxPrice})
    try:
        return result
    except IndexError:
        return None
