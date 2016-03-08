#Udacity Project 4 Hangman

## Set-Up Instructions:
1. Update the value of `application` in `app.yaml` to the app ID you
   have registered in the App Engine admin console and would like to use to host
   your instance of this sample.
2. Start Google App Engine Launcher, select [File]->[Add Existing Application] to app folder.
3. Run the app with App Launcher "RUN" button.
4. Test app with api explorer. Input URL: "http://localhost:8080/_ah/api/explorer"
5. In APIs Explorer page, select left "Service" then choose "hangman API" to test gmae.
6. Push "SDK Console" button on App Launcher, there are three useful check point for app debugging.
    * Datastore Indexes
    * Memcache Viewer
    * Task Queues
7. Using App Launcher "Deploy" button to Deploy your application.
 
##Game Description:
Hangman is a word guessing game. Game start with random select target word form 
word pool, and select game mode: 'hard', 'easy' or 'normal'. 'guess' is sending
character to the `make_move` endpoint which will reply several information:
 - 'attempts_count': how many times you guess.
 - 'guess_string' : show guess hit on specific character.
 - 'message' : notify the status of hangman.
Many different hangman can be played by many different users anytime. Each game
could be played or continued by using the `urlsafe_key` parameter.

Demo Link:
[p4-hangman-wats0n-160307.appspot.com/_ah/api/explorer](https://apis-explorer.appspot.com/apis-explorer/?base=https://p4-hangman-wats0n-160307.appspot.com/_ah/api#p/)

##Quick Play Instruction:
1. Select `hangman.create_user` to create user account.
2. Choose `hangman.new_game` to start a new game, game mode has 'hard', 'easy' and 'normal'(default).
3. Copy `urlsafe_key` form Response region.
4. Open `hangman.make_move' with `urlsafe_key` and make `guess` with one character.

##Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - main.py: Handler for taskqueue handler.
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.
 - words.txt: Word pool for `new_game` endpoint selection.
 
##Endpoints Included:
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name, email (optional)
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will 
    raise a ConflictException if a User with that user_name already exists.
    
 - **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: user_name, min, max, attempts
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game. user_name provided must correspond to an
    existing user - will raise a NotFoundException if not. Min must be less than
    max. Also adds a task to a task queue to update the average moves remaining
    for active games.
     
 - **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game.
    
 - **make_move**
    - Path: 'game/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key, guess
    - Returns: GameForm with new game state.
    - Description: Accepts a 'guess' and returns the updated state of the game.
    If this causes a game to end, a corresponding Score entity will be created.
    
 - **get_scores**
    - Path: 'scores'
    - Method: GET
    - Parameters: None
    - Returns: ScoreForms.
    - Description: Returns all Scores in the database (unordered).
    
 - **get_user_scores**
    - Path: 'scores/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: ScoreForms. 
    - Description: Returns all Scores recorded by the provided player (unordered).
    Will raise a NotFoundException if the User does not exist.
    
 - **get_active_game_count**
    - Path: 'games/active'
    - Method: GET
    - Parameters: None
    - Returns: StringMessage
    - Description: Gets the average number of attempts remaining for all games
    from a previously cached memcache key.

 - **get_user_games**
    - Path: 'games/user/{user_name}'
    - Method: GET
    - Parameters: USER_REQUEST
    - Returns: GameListForms
    - This returns all of a User's active games.
    
 - **cancel_game**
    - Path: 'game/del/{urlsafe_game_key}'
    - Method: GET
    - Parameters: GET_GAME_REQUEST
    - Returns: StringMessage
    - This endpoint allows users to cancel a game in progress, and reture success/fail information.
    
 - **get_high_scores**
    - Path: 'high_scores'
    - Method: GET
    - Parameters: GET_HIGH_SCORE_REQUEST
    - Returns: ScoreForms
    - generate a list of high scores in descending order.
    - Accept an optional parameter `number_of_results` that limits the number of results returned.
    
 - **get_user_rankings**
    - Path: 'user_rankings'
    - Method: GET
    - Parameters: None
    - Returns: UserRankForms
    - Ranking all player in descending order by normalized score (norm_score).
    - norm_score = 
    ((remaing attempt number)-((current attempt number) - (word length)))/(((word length)+(attempt limit form game mode))/2)
 
 - **get_game_history**
    - Path: 'game_history/{urlsafe_game_key}'
    - Method: GET
    - Parameters: GET_GAME_REQUEST
    - Returns: GameHistoryForms
    - Your API Users may want to be able to see a 'history' of moves for each game.
    - For example, guesst 'o', 'h', 'e', 'l' for "hello" word:
    ["message": "Guess o, Result:____o", "message": "Guess h, Result:h___o",
    message": "Guess e, Result:he__o", "message": "Guess l, Result:hello"].

##Models Included:
 - **User**
    - Stores unique user_name and (optional) email address.
    - BUt only has email account would receive active game notification.
    
 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.
    
 - **Score**
    - Records completed games. Associated with User and Game model via KeyProperty.
    
##Forms Included:
 - **GameForm**
    - Representation of a Game's state (urlsafe_key, attempts_remaining,
    game_over flag, message, user_name).
 - **NewGameForm**
    - Used to create a new game (user_name, min, max, attempts)
 - **MakeMoveForm**
    - Inbound make move form (guess).
 - **ScoreForm**
    - Representation of a completed game's Score (user_name, date, won flag,
    guesses).
 - **ScoreForms**
    - Multiple ScoreForm container.
 - **StringMessage**
    - General purpose String container.
 - **GameListForm**
    - A urlsafe_key container for listing active game for specific user.
 - **GameListForms**
    - Multiple GameListForm container.
 - **UserRankForm**
    - Store user name and normalized score for ordering ranking.
 - **UserRankForms**
    - Multiple UserRankForm container.
 - **GameHistoryForms**
    - Generate game history guess progress.

##Creator
------
_Watson Huang (**wats0n**)_
_02/22, 2016_