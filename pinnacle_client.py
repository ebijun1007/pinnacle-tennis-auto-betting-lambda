import os
import datetime
import pinnacle
import slackweb
import traceback


class PinnacleClient():
    SLACK = slackweb.Slack(url=os.environ.get('SLACK_WEBHOOK_URL'))
    TENNIS_ID = 33
    PERIOD_NUMBER = 0
    IGNORE_WORD = ["ITF", "Doubles"]
    TODAY = datetime.datetime.now()
    TOMORROW = TODAY + datetime.timedelta(1)
    YESTERDAY = TODAY - datetime.timedelta(1)
    LAST_WEEK = TODAY - datetime.timedelta(7)
    LAST_MONTH = TODAY - datetime.timedelta(30)

    def __init__(self, username, password):
        self.api = pinnacle.APIClient(username, password)
        self.tennis_events = self.load_matches()
        self.current_open_bets = self.get_bets(from_date=self.LAST_WEEK)
        self.bets_history = self.get_bets()


    def load_matches(self):
        return self.api.market_data.get_fixtures(self.TENNIS_ID)

    def get_bets(self, from_date=YESTERDAY, to_date=TOMORROW, betlist=pinnacle.enums.BetListType.Running.value, bet_status=pinnacle.enums.BetStatusesType.Accepted.value):
        try:
            response = self.api.betting.get_bets(from_date=from_date, to_date=to_date, betlist=betlist, bet_statuses=bet_status)
            return response.get("straightBets", [])
        except Exception as e:
            if self.SLACK:
                self.SLACK.notify(text=str(e))

    def check_dup(self, home, away):
        for event in self.current_open_bets:
            if self.is_same_name(home, event["team1"]) and self.is_same_name(away, event["team2"]):
                return True
        return False

    def search_event(self, home, away):
        for league in self.tennis_events["league"]:
            if any(word in league["name"] for word in self.IGNORE_WORD):
                continue
            for event in league["events"]:
                if any(word in "".join([event["home"], event["away"]]) for word in ["(Games)", "of Set", "+1.5 Sets", "(Sets)"]):
                    continue
                if self.is_same_name(home, event["home"]) and self.is_same_name(away, event["away"]):
                    return league["id"], event["id"]
        return None, None

    def is_same_name(self, name1, name2):
        try:
            name1_parts = name1.lower().replace('-', ' ').split()
            name1_parts.sort()
            name2_parts = name2.lower().replace('-', ' ').split()
            name2_parts.sort()
            print(name1_parts, name2_parts)
            return name1_parts == name2_parts
        except Exception as e:
            if self.SLACK:
                self.SLACK.notify(text=str(e))
            return False

    def get_line(self, league_id, event_id, team):
        return self.api.market_data.get_line(
            league_id=league_id,
            event_id=event_id,
            team=team,
            sport_id=self.TENNIS_ID,
            bet_type=pinnacle.enums.BetType.MoneyLine.value,
            period_number=self.PERIOD_NUMBER
        )

    def place_bet(self, line_id, event_id, team, stake):
        return self.api.betting.place_bet(
            team=team,
            event_id=event_id,
            line_id=line_id,
            stake=stake,
            bet_type=pinnacle.enums.BetType.MoneyLine.value,
            sport_id=self.TENNIS_ID,
            period_number=self.PERIOD_NUMBER,
            fill_type=pinnacle.enums.FillType.Normal.value
        )

    def execute(self, home, away, team, stake):
        try:
            # if self.check_dup(home, away):
            #     raise Exception("Item is duplicated")
            league_id, event_id = self.search_event(home, away)
            if not league_id:
                raise Exception("League Not Found", home, away)
            line = self.get_line(league_id, event_id, team)
            bet = self.place_bet(line["lineId"], event_id, team, stake)
            if(error := bet.get("errorCode")):
                if (error == "INSUFFICIENT_FUNDS"):
                    raise Exception("INSUFFICIENT_FUNDS")
            if self.SLACK:
                self.SLACK.notify(text=str(bet))
            return bet
        except Exception as e:
            if self.SLACK:
                self.SLACK.notify(text=f"{home} vs {away}: {str(e)}")
                self.SLACK.notify(text=str(traceback.format_exc()))
            return e

    def show_current_open_bets(self):
        count = 0
        # sort by teamName
        self.current_open_bets.sort(key=lambda x: x["teamName"])
        for event in self.current_open_bets:
            if not (event.get("settledAt")):
                home = event["teamName"]
                if home == event["team1"]:
                    away = event["team2"]
                else:
                    away = event["team1"]
                count += 1
                print(f"[{home}] vs [{away}]: {event['risk']}@{event['price']}")
        print(count)

    def calc_roi(self):
        roi = 0
        auto_bet_roi = 0
        auto_win_count = 0
        auto_lose_count = 0
        won_events = self.get_bets(from_date=self.YESTERDAY, to_date=self.TODAY, betlist=pinnacle.enums.BetListType.Settled.value,
                                   bet_status=[pinnacle.enums.BetStatusesType.Won.value])
        lost_events = self.get_bets(from_date=self.YESTERDAY, to_date=self.TODAY, betlist=pinnacle.enums.BetListType.Settled.value,
                                    bet_status=[pinnacle.enums.BetStatusesType.Lose.value])
        events = won_events + lost_events
        for event in events:
                try:
                    roi += event.get("winLoss")
                    if event.get("risk") == 500:
                        home = event["teamName"]
                        if home == event["team1"]:
                            away = event["team2"]
                        else:
                            away = event["team1"]
                        print(f"[{home}] vs [{away}]: {event['risk']}@{event['price']}, {round(event['winLoss'], 2)}")
                        auto_bet_roi += event.get("winLoss")
                        auto_win_count += 1 if event.get("winLoss") > 0 else 0
                        auto_lose_count += 1 if event.get("winLoss") < 0 else 0
                except:
                    print(event)
                    continue
        # print(f"ROI: {round(roi, 2)}")
        print(f"Auto Bet ROI: {round(auto_bet_roi, 2)}")
        print(f"Auto Bet Win Ratio: {round(auto_win_count / (auto_win_count + auto_lose_count) * 100, 2)}% (Win: {auto_win_count}, Lose: {auto_lose_count}))")

if __name__ == "__main__":
    username = os.environ.get("PINNACLE_USERNAME")
    password = os.environ.get("PINNACLE_PASSWORD")

    # home = input("home: ")
    # away = input("away: ")
    # team = input("team: ")
    # stake = input("stake: ")

    home = "daniel-taro"
    away = "hong-seong-chan"
    team = "Team1"
    stake = 200

    client = PinnacleClient(username, password)
    client.calc_roi()
    client.show_current_open_bets()

    # response = client.execute(home, away, team, stake)
    # print(response)
