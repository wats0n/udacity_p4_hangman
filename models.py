"""models.py - This file contains the class definitions for the Datastore
entities used by the Game. Because these classes are also regular Python
classes they can include methods (such as 'to_form' and 'new_game')."""

import random
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb

from utils import get_by_urlsafe

class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email =ndb.StringProperty()

class Game(ndb.Model):
    """Game object"""
    user = ndb.KeyProperty(required=True, kind='User')
    target_word = ndb.StringProperty(required=True)
    attempts_count = ndb.IntegerProperty(required=True, default=0)
    attempts_progress = ndb.IntegerProperty(required=True, default=2)
    attempts_limit = ndb.IntegerProperty(required=True, default=8)
    game_over = ndb.BooleanProperty(required=True, default=False)
    history = ndb.PickleProperty(required=True)

    @classmethod
    def new_game(cls, user, target_word, attempts_progress, attemps_limit):
        """Creates and returns a new game"""
        game = Game(user=user,
                    target_word= target_word,
                    attempts_count = 0,
                    attempts_progress = attempts_progress,
                    attempts_limit = attemps_limit,
                    game_over = False)
        game.history = []
        game.put()
        return game

    def to_form(self, message, guess_string):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.user.get().name
        form.attempts_count = self.attempts_count
        form.game_over = self.game_over
        form.message = message
        form.guess_string = guess_string
        form.history = str(self.history)
        return form

    def to_listform(self):
        """Returns a GameForm representation of the Game"""
        form = GameListForm()
        form.urlsafe_key = self.key.urlsafe()
        return form

    def end_game(self, won=False):
        """Ends the game - if won is True, the player won. - if won is False,
        the player lost."""
        self.game_over = True
        self.put()
        slen = len(self.target_word);
        norm_score = ((self.attempts_limit-self.attempts_progress))
        norm_score -= (self.attempts_count-slen)
        norm_score = float(norm_score)/((slen+self.attempts_limit)/2)
        # Add the game to the score lise
        score = Score(user=self.user, date=date.today(), won=won,
                guess_count=self.attempts_count,
                guess_remaing=self.attempts_limit-self.attempts_progress,
                norm_score=norm_score, game=self.key)
        score.put()


class Score(ndb.Model):
    """Score object"""
    user = ndb.KeyProperty(required=True, kind='User')
    date = ndb.DateProperty(required=True)
    won = ndb.BooleanProperty(required=True)
    guess_count = ndb.IntegerProperty(required=True)
    guess_remaing = ndb.IntegerProperty(required=True)
    norm_score = ndb.FloatProperty(required=True)
    game = ndb.KeyProperty(required=True, kind='Game')
    
    def to_form(self):
        return ScoreForm(user_name=self.user.get().name, won=self.won,
                         date=str(self.date), guess_count=self.guess_count,
                         guess_remaing=self.guess_remaing,
                         history=str(self.game.get().history),
                         norm_score=self.norm_score,
                         word=self.game.get().target_word,
                         game_url=self.game.urlsafe())


class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    attempts_count = messages.IntegerField(2, required=True)
    game_over = messages.BooleanField(3, required=True)
    message = messages.StringField(4, required=True)
    user_name = messages.StringField(5, required=True)
    guess_string = messages.StringField(6, required=True)
    history = messages.StringField(7, required=True)


class NewGameForm(messages.Message):
    """Used to create a new game"""
    user_name = messages.StringField(1, required=True)
    mode = messages.StringField(2, default='normal')


class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    guess = messages.StringField(1, required=True)


class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    user_name = messages.StringField(1, required=True)
    date = messages.StringField(2, required=True)
    won = messages.BooleanField(3, required=True)
    guess_count = messages.IntegerField(4, required=True)
    guess_remaing = messages.IntegerField(5, required=True)
    history = messages.StringField(6, required=True)
    norm_score = messages.FloatField(7, required=True)
    word = messages.StringField(8, required=True)
    game_url = messages.StringField(9, required=True)


class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)

class GameListForm(messages.Message):
    """Active game entry for specific user."""
    urlsafe_key = messages.StringField(1, required=True)

class GameListForms(messages.Message):
    """Return multiple game entries."""
    items = messages.MessageField(GameListForm, 1, repeated=True)

class UserRankForm(messages.Message):
    """User Ranking Information"""
    user_name = messages.StringField(1, required=True)
    avg_score = messages.FloatField(2, required=True)
    
class UserRankForms(messages.Message):
    """Return User Ranking List"""
    items = messages.MessageField(UserRankForm, 1, repeated=True)

class GameHistoryForms(messages.Message):
    """Return Guess History"""
    items = messages.MessageField(StringMessage, 1, repeated=True)
