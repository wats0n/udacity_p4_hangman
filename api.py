"""api.py - Create and configure the Game API exposing the resources.
This can also contain game logic. For more complex games it would be wise to
move game logic to another file. Ideally the API will be simple, concerned
primarily with communication to/from the API's users."""


import logging
import endpoints
import random
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import User, Game, Score
from models import StringMessage, NewGameForm, GameForm, MakeMoveForm,\
    ScoreForms, GameListForm, GameListForms, UserRankForm, UserRankForms,\
    GameHistoryForms
from utils import get_by_urlsafe

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))

GET_HIGH_SCORE_REQUEST = endpoints.ResourceContainer(
     number_of_results=messages.IntegerField(1),)

MEMCACHE_MOVES_REMAINING = 'MOVES_REMAINING'

hangman_msg = [
    'Setup Gallow~',
    'Setup Haning String~',
    'Draw Head~',
    'Draw Left Hand~',
    'Draw Right Hand~',
    'Draw Stick Body~',
    'Draw Left Leg~',
    'Draw Right Leg~',
    'Draw Left Eye~',
    'Draw Right Eye~',
    'Draw Middle Mouth~',
]

@endpoints.api(name='hangman', version='v1')
class HangmanApi(remote.Service):
    """Game API"""
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                    'A User with that name already exists!')
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message='User {} created!'.format(
                request.user_name))

    def _choose_random_word(self, word_file):
        """ Choose random word from then file contained words."""
        return random.choice(open(word_file).readlines()).strip(' \t\n\r')
    
    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        
        if(request.mode.lower() == "easy"):
            progress = 0
            limit = 11
            msg = 'Hangman easy mode! Start form building gallow.'
        elif(request.mode.lower() == "hard"):
            progress = 2
            limit = 8
            msg = 'Hangman hard mode!'
            msg += ' Start from man part without face and foot.'
        else:
            # Normal Mode
            progress = 2
            limit = 11
            msg = 'Hangman normal mode!'
            msg += ' Start from man part with face and foot.'
        word = self._choose_random_word('words.txt')
        game = Game.new_game(user.key, word.lower(), progress, limit)

        # Use a task queue to update the average attempts remaining.
        # This operation is not needed to complete the creation of a new game
        # so it is performed out of sequence.
        taskqueue.add(url='/tasks/cache_average_attempts')
        return game.to_form(msg, '_'*len(game.target_word))

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            guess_string = ''
            for s in game.target_word:
                if(s in game.history):
                    guess_string += s
                else:
                    guess_string += '_'
            if(game.game_over == True):
                if (guess_string == game.target_word):
                    return game.to_form('You Win!', guess_string)
                else:
                    return game.to_form('Game Over!', guess_string)
            else:
                return game.to_form(hangman_msg[game.attempts_progress]+
                                ' ,Time to make a move!', guess_string)
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        
        if game.game_over:
            return game.to_form('Game already over!', game.target_word)

        lguess = request.guess.lower()
        
        if(len(lguess) == 0):
            raise endpoints.BadRequestException('Please input character!')
        else:
            if(lguess[0] in game.history):
                guess_string = ''
                for s in game.target_word:
                    if(s in game.history):
                        guess_string += s
                    else:
                        guess_string += '_'
                return game.to_form(str(request.guess[0])+",has been submit",
                                    game.target_word)
            else:
                game.history.append(request.guess[0])

        game.attempts_count += 1
        if not (lguess[0] in game.target_word):
            game.attempts_progress += 1;
        
        guess_string = ''
        for s in game.target_word:
            if(s in game.history):
                guess_string += s
            else:
                guess_string += '_'
        
        if (guess_string == game.target_word):
            game.end_game(True);
            return game.to_form('You win! Still Alive!', guess_string)
        
        if (game.attempts_progress >= game.attempts_limit):
            game.end_game(False)
            return game.to_form(hangman_msg[game.attempts_progress] +
                                ' Game over!', game.target_word)
        else:
            game.put()
            return game.to_form(hangman_msg[game.attempts_progress] +
                                ' then next move', guess_string)

    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all scores"""
        return ScoreForms(items=[score.to_form() for score in Score.query()])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=ScoreForms,
                      path='scores/user/{user_name}',
                      name='get_user_scores',
                      http_method='GET')
    def get_user_scores(self, request):
        """Returns all of an individual User's scores"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        scores = Score.query(Score.user == user.key)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(response_message=StringMessage,
                      path='games/average_attempts',
                      name='get_average_attempts_remaining',
                      http_method='GET')
    def get_average_attempts(self, request):
        """Get the cached average moves remaining"""
        return StringMessage(message=memcache.get(MEMCACHE_MOVES_REMAINING) or '')

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameListForms,
                      path='games/user/{user_name}',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Returns all of an individual User's game entry."""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        games = Game.query(Game.user == user.key)
        games = games.filter(Game.game_over == False)
        return GameListForms(items=[game.to_listform() for game in games])

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=StringMessage,
                      path='game/del/{urlsafe_game_key}',
                      name='cancel_game',
                      http_method='GET')
    def cancel_game(self, request):
        """Cancel playing game."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            if(game.game_over == False):
                game.key.delete()
                return StringMessage(message="Game cancelled.")
            else:
                return StringMessage(message="Game has been finished.")
        else:
            raise endpoints.NotFoundException('Game not found!')
        
    @endpoints.method(request_message=GET_HIGH_SCORE_REQUEST,
                      response_message=ScoreForms,
                      path='high_scores',
                      name='get_high_scores',
                      http_method='GET')
    def get_high_scores(self, request):
        """Return high scores"""
        scores = Score.query()
        scores = scores.order(-Score.norm_score)
        scores = scores.fetch(limit=request.number_of_results);
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(response_message=UserRankForms,
                      path='user_rankings',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Return user ranking"""
        users = User.query()
        avg_rank = []
        for u in users:
            scores = Score.query(Score.user == u.key)
            avg = 0.0
            for s in scores:
                avg += s.norm_score
            avg /= scores.count()
            avg_rank.append([avg, u.name])
        avg_rank = sorted(avg_rank, reverse=True)
        return UserRankForms(items=[UserRankForm(user_name=a[1],
            avg_score=a[0]) for a in avg_rank])

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameHistoryForms,
                      path='game_history/{urlsafe_game_key}',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Return detail game history."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            hlist = []
            for i in range(len(game.history)):
                subhist = game.history[:i+1]
                guess_string = ''
                for s in game.target_word:
                    if(s in subhist):
                        guess_string += s
                    else:
                        guess_string += '_'
                msg = 'Guess %s, Result:%s' % (game.history[i],\
                                               guess_string)
                hlist.append(StringMessage(message=msg))
            return GameHistoryForms(items=hlist)
        else:
            raise endpoints.NotFoundException('Game not found!')
    
    
    @staticmethod
    def _cache_average_attempts():
        """Populates memcache with the average moves remaining of Games"""
        games = Game.query(Game.game_over == False).fetch()
        if games:
            count = len(games)
            total_attempts_count = sum([game.attempts_limit-\
                                        game.attempts_progress for game in games])
            average = float(total_attempts_count)/count
            memcache.set(MEMCACHE_MOVES_REMAINING,
                         'The average moves remaining is {:.2f}'.format(average))


api = endpoints.api_server([HangmanApi])
