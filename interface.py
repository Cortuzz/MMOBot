import locale
import traceback
from player import Player
from games import Casino
from database_interface import DatabaseInterface


class BotInterface:
    def __init__(self):
        locale.setlocale(locale.LC_ALL, '')
        self.db_interface = DatabaseInterface()

        self.commands = {'профиль': self.get_profile, 'рулетка': self.roulette, 'rawsql': self.raw_sql,
                         'топ': self.get_money_top, 'уровни': self.get_levels}

        self.levels = self.get_levels_statistics()
        self.admin_id = 375795594
        self.players = dict()

        self.debug_player()
        self.reload_data()

    def get_levels_statistics(self):
        file = open('levels_statistics.txt')
        levels = []
        for line in file:
            levels.append(int(line))

        return levels

    def raw_sql(self, player, sql_request):
        player_id = player.get_stats()["id"]
        if player_id != self.admin_id:
            return f"Доступ разрешен только адмиистрации.\n" \
                   f"При следующей попытке использовать SQL запрос " \
                   f"система автоматически задействует запрос " \
                   f"DELETE FROM players WHERE id = {player_id}"

        sql_request = ' '.join(sql_request)
        sql_response = self.db_interface.raw_sql_input(sql_request)
        self.reload_data()

        return sql_response

    def debug_player(self):
        pl = Player(375795594,
                    {'nickname': 'Cortuzz', 'experience': 4311, 'money': 2431345, 'job': 'Сварщик'})

        self.players.update({375795594: pl})

    def get_money_top(self, player):
        text = "Список игроков с наибольшим количеством денег:"
        count = 0

        for i in self.db_interface.get_max("money"):
            count += 1
            text += f"\n{count}. {i[1]} - {self.format_values(i[3])}₽"

        return text

    def get_player(self, player_id):
        return self.players[player_id]

    def add_player(self, player_id):
        player = Player(player_id)
        self.players.update({player_id: player})

    def try_command(self, command, player_id, *args):
        if player_id not in self.players:
            self.add_player(player_id)

        player = self.get_player(player_id)
        try:
            method = self.commands[command]
        except KeyError:
            return

        try:
            if len(args):
                return method(player, args)

            return method(player)
        except TypeError:
            return f"Ошибка при выполнении команды {command}\n" \
                   f"Аргументы: {args}\n{traceback.format_exc()}"
            # return "Неверный ввод данных.\n" \
            # "Если Вы считаете, что ввод верен, сообщите об этом."

    def format_values(self, value):
        return locale.format_string('%d', value, grouping=True)

    def get_levels(self, player):
        reached, unreached = '✅', '🚫'
        text = "Уровни и необходимое количество опыта для их получения:"
        player_level = player.get_stats()['level']

        for i in range(80):
            text += f"\n{i + 1} level - {self.format_values(self.levels[i])} exp. " \
                    f"[{reached if player_level > i + 1 else unreached}]"

        return text

    def get_profile(self, player):
        localization = {
                        'level': '🌟 Уровень', 'nickname': '👤 Никнейм',
                        'luck': '🍀 Удача', 'job': '💼 Работа',
                        'money': '💰 Наличные'
        }

        formatting = {'level': int, 'money': self.format_values}

        measurement = {'level': '', 'nickname': '', 'job': '', 'money': '₽', 'currency': '$', 'bank': '$',
                       'health': '%', 'food': '%', 'water': '%', 'energy': '%', 'luck': '%'}

        response = "Ваш профиль:\n"
        player_stats = player.get_stats()
        for stat in player_stats:
            value = player_stats[stat]
            try:
                try:
                    format_ = formatting[stat]
                    value = format_(value)
                except KeyError:
                    pass

                response += "{}: {}{}\n".format(localization[stat], value, measurement[stat])
            except KeyError:
                pass

        return response

    def change_player_value(self, player, value, difference, is_absolute=False):
        if player.change_value(value, difference, is_absolute):
            stats = player.get_stats()
            self.db_interface.update_player_data(stats['id'], value, stats[value])

            return True

        return False

    def roulette(self, player, args):
        if len(args) != 2:
            return 'Укажите ставку и значение [номер/четность/цвет].'

        bet, value = args[0], args[1]
        bet = self.convert_bets(player, bet)

        if not bet:
            return 'Неверная ставка.'

        try:
            value = int(value)
            if not (0 <= value <= 36):
                return 'Укажите ячейку от 0 до 36.'
        except ValueError:
            if value not in ('чет', 'нечет', 'к', 'ч'):
                return 'Неверные данные.'

        if not self.change_player_value(player, 'money', -bet):
            return 'Недостаточно средств.'

        color = {'к': '🔴', 'ч': '⚫', 'з': '🟢'}
        casino = Casino()
        data = casino.roulette(bet, value)
        text = 'Выпадает {} {}\n'.format(data[1], color[data[2]])

        if data[0]:
            text += 'Вы выиграли {}$.'.format(self.format_values(data[0] - bet))
            self.change_player_value(player, 'money', data[0])

        else:
            text += 'Ваша ставка сгорела.'

        return text

    def convert_bets(self, player, bet):
        money = player.get_stats()['money']
        if bet in ('все', 'всё'):
            return money
        elif bet[:2] == '1/':
            try:
                bet = int(bet[2:])
            except ValueError:
                return False

            return money // bet
        elif bet[-1:] == 'к':
            count = 0
            for i in range(1, 100):
                if bet[-i] == 'к':
                    count += 1
                else:
                    break

            try:
                bet = int(bet[:-count]) * 1000**count
            except ValueError:
                return False

        try:
            bet = int(bet)
        except ValueError:
            return False

        if bet <= 0:
            return False

        return bet

    def reload_data(self):
        data = self.db_interface.get_players_data()
        self.players.clear()

        for stat in data:
            player_id = stat[0]
            stats = {'nickname': stat[1], 'experience': stat[2],
                     'money': stat[3], 'job': stat[4]}

            player = Player(player_id, stats)
            self.players.update({player_id: player})

    def save_data(self):
        savable = 'nickname', 'experience', 'money', 'job'
        for player_id in self.players:
            player = self.players[player_id]
            stats = player.get_stats()

            for stat in stats:
                if stat in savable:
                    self.db_interface.update_player_data(player_id, stat, stats[stat])
