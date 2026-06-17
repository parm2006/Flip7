import random
import sys
import builtins

def custom_input(prompt=""):
    try:
        val = builtins.input(prompt)
        if val.strip().lower() == "exit":
            print("\nExiting game cleanly. Goodbye!")
            sys.exit(0)
        return val
    except (KeyboardInterrupt, EOFError):
        print("\nExiting game cleanly. Goodbye!")
        sys.exit(0)

# Overload the built-in input function
input = custom_input

class Card:
    def __init__(self, value, special=None):
        self.value = value
        self.special = special

    def __str__(self):
        if self.special:
            return f"{self.special}"
        else:
            return f"{self.value}"
        
    def __repr__(self):
        return self.__str__()
    

class Deck:
    def __init__(self):
        self.cards = [] # queue of cards in the deck( pop first to deal)
        self.discards = [] # discard pile

    def generate(self):
        from random import shuffle

        cards = []
        j = 1

        while j <= 12:
            for _ in range(1, j+1): # add one thru 12
                cards.append(Card(j))
            j += 1
        
        cards.append(Card(0, "CHANGETHEFUTURE(3)")) # add 0 (Change the Future card)
        cards.append(Card(0, "PLUS2")) # add specials
        cards.append(Card(0, "PLUS4"))
        cards.append(Card(0, "PLUS6"))
        cards.append(Card(0, "PLUS8"))
        cards.append(Card(0, "PLUS10"))
        cards.append(Card(0, "TIMES2"))
        for i in range(1, 4): # add three of each special
            cards.append(Card(0, "FLIP3"))
            cards.append(Card(0, "FREEZE"))
            cards.append(Card(0, "SECONDCHANCE"))

        shuffle(cards) # shuffle the deck
        print("Deck generated and shuffled.")
        self.cards = cards
        return self

    def draw(self):
        if not self.cards:
            self.shuffle_discards()
        if not self.cards:
            raise RuntimeError("The deck and discard pile are completely empty!")
        return self.cards.pop(0)

    def shuffle_discards(self):
        from random import shuffle
        if not self.discards:
            return
        print("\n[System] Shuffling discard pile back into the deck...")
        self.cards.extend(self.discards)
        self.discards = []
        shuffle(self.cards)


class Hand:
    def __init__(self):
        self.name = None
        self.cards = []
        self.specialcards = []
        self.status = "active" # active, frozen, secondchance, busted, stay
        self.value = 0 # total value of the hand (sum of number cards)

    def hit(self, card, deck=None, all_players=None):
        if card.special:
            if card.special == "CHANGETHEFUTURE(3)":
                # CHANGETHEFUTURE(3) acts as a number card with value 0 for Flip 7 check
                # There is only 1 in the deck, so no duplicate check is needed
                self.cards.append(card)
                self.value += card.value
                
                if deck and all_players:
                    self.activate_special_effect(card, deck, all_players)
                
                if len(self.cards) == 7:
                    self.status = "flipped7"
                    print(f"Game is over!. {self.name} has Flipped 7")
                    print("Updating Leaderboard")
            elif card.special == "SECONDCHANCE":
                self.specialcards.append(card)
                # Goes to self by default unless they already have one
                sc_count = sum(1 for c in self.specialcards if c.special == "SECONDCHANCE")
                if sc_count > 1:
                    # Drawer already has one, they must give the extra to someone else
                    if deck and all_players:
                        self.activate_special_effect(card, deck, all_players)
            else:
                self.specialcards.append(card)
                if deck and all_players:
                    self.activate_special_effect(card, deck, all_players)
        else:
            # Duplicate check only for the card that was immediately drawn
            is_duplicate = any(c.value == card.value for c in self.cards)
            self.cards.append(card)
            self.value += card.value
            
            if is_duplicate:
                self.status = "busted"
                # Do not print busted yet; check_and_resolve_bust will print/handle it if not saved.
            elif len(self.cards) == 7:
                self.status = "flipped7"
                print(f"Game is over!. {self.name} has Flipped 7")
                print("Updating Leaderboard")

    def activate_special_effect(self, card, deck, all_players):
        if card.special == "CHANGETHEFUTURE(3)":
            rearrange_future(deck, self)
        elif card.special == "FREEZE":
            select_and_freeze(self, card, all_players)
        elif card.special == "FLIP3":
            resolve_flip_three(self, all_players, deck)
        elif card.special == "SECONDCHANCE":
            give_second_chance(self, card, all_players)


class Leaderboard:
    def __init__(self, players):
        self.scores = {} # dictionary of player names and their scores
        for player in players:
            self.scores[player] = 0

    def update_scores(self, round_values):
        for player, val in round_values.items():
            self.scores[player] += val

    def print_leaderboard(self, round_values=None):
        print("\n" + "=" * 65)
        print("                           LEADERBOARD")
        print("=" * 65)
        print(f"{'Player Name':<20} | {'Prev Total':<12} | {'Round Score':<12} | {'New Total':<10}")
        print("-" * 65)
        for player in self.scores:
            round_val = round_values.get(player, 0) if round_values else 0
            new_total = self.scores[player]
            prev_total = new_total - round_val
            print(f"{player:<20} | {prev_total:<12} | {round_val:<12} | {new_total:<10}")
        print("=" * 65 + "\n")


def check_and_resolve_bust(player, card, deck):
    if player.status == "busted":
        has_sc = any(c.special == "SECONDCHANCE" for c in player.specialcards)
        if has_sc:
            # Revert bust silently (no busted print)
            player.cards.remove(card)
            player.value -= card.value
            sc_card = next(c for c in player.specialcards if c.special == "SECONDCHANCE")
            player.specialcards.remove(sc_card)
            deck.discards.append(card)
            deck.discards.append(sc_card)
            player.status = "active"
            print(f"  --> {player.name} was saved by Second Chance! Duplicate {card.value} and Second Chance cards discarded.")
            return True # saved
        else:
            # Set value to 0 right then when actually busted
            player.value = 0
            print(f"  --> {player.name} has busted on a {card.value}!")
            return False # busted
    return True # active


def select_and_freeze(chooser, card, all_players):
    active_players = [p for p in all_players if p.status == "active"]
    if not active_players:
        print("  No active players available to freeze.")
        return
    
    print(f"\n--- Freeze Selection ---")
    print(f"{chooser.name} drew FREEZE! Choose a player to freeze:")
    for idx, p in enumerate(active_players):
        print(f"  {idx + 1}: {p.name}")
        
    while True:
        try:
            choice = int(input(f"{chooser.name}, select player to freeze: ")) - 1
            if 0 <= choice < len(active_players):
                target = active_players[choice]
                break
            else:
                print(f"Please select a number between 1 and {len(active_players)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        
    target.status = "frozen"
    # Transfer Freeze card to target's specialcards
    if card in chooser.specialcards:
        chooser.specialcards.remove(card)
    target.specialcards.append(card)
    print(f"  --> {target.name} has been FROZEN, and the FREEZE card is placed in their hand!")


def give_second_chance(chooser, card, all_players):
    # Chooser drew an extra Second Chance, they already have one.
    # Valid players are anyone who is not busted, frozen, or stayed, and doesn't already have one
    eligible_players = [
        p for p in all_players 
        if p != chooser 
        and p.status == "active" 
        and not any(c.special == "SECONDCHANCE" for c in p.specialcards)
    ]
    
    if not eligible_players:
        # Fallback: active players who already have one
        eligible_players = [p for p in all_players if p != chooser and p.status == "active"]
        
    if not eligible_players:
        print(f"  --> No other active players to give Second Chance to. Extra Second Chance discarded.")
        if card in chooser.specialcards:
            chooser.specialcards.remove(card)
        return

    print(f"\n--- Give Second Chance ---")
    print(f"{chooser.name} drew an extra SECOND CHANCE! Choose an active player to give it to:")
    for idx, p in enumerate(eligible_players):
        print(f"  {idx + 1}: {p.name}")
        
    while True:
        try:
            choice = int(input(f"{chooser.name}, select player: ")) - 1
            if 0 <= choice < len(eligible_players):
                target = eligible_players[choice]
                break
            else:
                print(f"Please select a number between 1 and {len(eligible_players)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        
    # Transfer Second Chance
    if card in chooser.specialcards:
        chooser.specialcards.remove(card)
    target.specialcards.append(card)
    print(f"  --> {chooser.name} gave Second Chance to {target.name}!")


def rearrange_future(deck, player):
    # If the deck has fewer than 3 cards, shuffle discards and put them on the bottom of deck.cards
    if len(deck.cards) < 3:
        if deck.discards:
            from random import shuffle
            print("\n[System] Shuffling discard pile and placing it at the bottom of the deck...")
            shuffled_discards = list(deck.discards)
            shuffle(shuffled_discards)
            deck.cards.extend(shuffled_discards)
            deck.discards = []
            
    num_cards_to_see = min(3, len(deck.cards))
    if num_cards_to_see == 0:
        print("  Deck is empty and there are no discards. Cannot change the future.")
        return
        
    top_cards = deck.cards[:num_cards_to_see]
    print(f"\n--- Change the Future (Top {num_cards_to_see} cards) ---")
    print(f"{player.name} drew CHANGETHEFUTURE(3)! Here are the top cards of the deck:")
    for idx, c in enumerate(top_cards):
        print(f"  {idx + 1}: {c}")
        
    print("How would you like to rearrange them?")
    print("Enter the indices in the order you want them on top (e.g., '1,2,3' or '2,3,1').")
    print("The first card you specify will be the very next card drawn.")
    
    while True:
        user_input = input("Enter new order: ")
        try:
            indices = [int(x.strip()) - 1 for x in user_input.split(",")]
            if len(indices) == num_cards_to_see and sorted(indices) == list(range(num_cards_to_see)):
                new_top = [top_cards[i] for i in indices]
                deck.cards[:num_cards_to_see] = new_top
                print("  --> Future rearranged successfully!")
                break
        except ValueError:
            pass
        print(f"Invalid input. Enter exactly {num_cards_to_see} distinct numbers from 1 to {num_cards_to_see} separated by commas.")


def resolve_flip_three(chooser, all_players, deck):
    active_players = [p for p in all_players if p.status == "active"]
    if not active_players:
        print("  No active players available to target with Flip Three.")
        return
    
    print(f"\n--- Flip Three Target Selection ---")
    print(f"{chooser.name} drew FLIP3! Choose a target player for Flip Three:")
    for idx, p in enumerate(active_players):
        print(f"  {idx + 1}: {p.name}")
        
    while True:
        try:
            choice = int(input(f"{chooser.name}, select target player number: ")) - 1
            if 0 <= choice < len(active_players):
                target = active_players[choice]
                break
            else:
                print(f"Please select a number between 1 and {len(active_players)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    print(f"\n>>> Flip Three resolved on {target.name}! Dealing up to 3 cards...")
    
    target_flip_three_count = 0
    for i in range(3):
        if target.status != "active":
            break
            
        print(f"  Dealing card {i+1}/3 to {target.name}...")
        card = deck.draw()
        print(f"    {target.name} drew: {card}")
        
        if card.special == "FLIP3":
            target.hit(card, None, None)
            target_flip_three_count += 1
        else:
            target.hit(card, deck, all_players)
                
        check_and_resolve_bust(target, card, deck)
        
        if target.status == "flipped7":
            break
            
    # Resolve any Flip Threes earned by target
    for _ in range(target_flip_three_count):
        resolve_flip_three(target, all_players, deck)


def deal_card_to_player(deck, player, all_players):
    card = deck.draw()
    print(f"  {player.name} drew: {card}")
    
    player.hit(card, deck, all_players)
    
    check_and_resolve_bust(player, card, deck)


def calculate_hand_value(hand):
    if hand.status == "busted":
        return 0
        
    base_sum = sum(c.value for c in hand.cards)
    
    # TIMES2 modifier
    times_two_count = sum(1 for c in hand.specialcards if c.special == "TIMES2")
    multiplier = 2 ** times_two_count
    
    # PLUS modifiers
    plus_sum = 0
    for c in hand.specialcards:
        if c.special and c.special.startswith("PLUS"):
            try:
                val = int(c.special[4:])
                plus_sum += val
            except ValueError:
                pass
                
    round_val = base_sum * multiplier + plus_sum
    
    if hand.status == "flipped7":
        round_val += 15
        
    return round_val


def clear_screen_and_show_status(round_number, dealer_name, deck, hands):
    import os
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"=================================================================")
    print(f"               ROUND {round_number} STATUS BOARD")
    print(f"=================================================================")
    print(f"Dealer: {dealer_name}")
    print(f"Cards in deck: {len(deck.cards)} | Discard pile: {len(deck.discards)}")
    print("\n--- Current Hands ---")
    for name, hand in hands.items():
        status_str = f" ({hand.status.upper()})" if hand.status != "active" else ""
        print(f"  {name:<15}: Hand: {hand.cards} | Specials: {hand.specialcards} | Value: {hand.value}{status_str}")
    print("=================================================================\n")


def main():
    # Generate Deck
    deck = Deck()
    deck = deck.generate()

    # Clear screen at the very start of the game
    import os
    os.system('cls' if os.name == 'nt' else 'clear')

    while True:
        try:
            players = int(input("Enter number of players (2-13): "))
            if 2 <= players <= 13:
                break
        except ValueError:
            pass
        print("Invalid number of players. Please enter a number between 2 and 13.")
        
    player_names = []
    for i in range(players):
        while True:
            name = input(f"Player {i+1} Name: ").strip()
            if name and name not in player_names:
                player_names.append(name)
                break
            print("Invalid or duplicate name. Please enter a unique name.")
            
    hands = {}
    for name in player_names:
        hand = Hand()
        hand.name = name
        hands[name] = hand
        
    leaderboard = Leaderboard(player_names)
    
    # Pick first dealer at random
    dealer_idx = random.randint(0, len(player_names) - 1)
    
    print("\nStart Game")
    round_number = 1
    
    while True:
        dealer_name = player_names[dealer_idx]
        print(f"\n==========================================")
        print(f"               ROUND {round_number}")
        print(f"==========================================")
        print(f"Dealer: {dealer_name}")
        print(f"Cards in deck: {len(deck.cards)} | Discard pile: {len(deck.discards)}")
        
        # 1. Deal Phase (two rounds of forced hits)
        round_ended_early = False
        
        for round_num in range(1, 3):
            if round_ended_early:
                break
            for i in range(len(player_names)):
                # Deal starts with the player to the left of the dealer
                curr_idx = (dealer_idx + 1 + i) % len(player_names)
                curr_player = hands[player_names[curr_idx]]
                
                if curr_player.status == "active":
                    # Clear screen and show status before dealing
                    clear_screen_and_show_status(round_number, dealer_name, deck, hands)
                    print(f"Dealing card {round_num} to {curr_player.name}...")
                    
                    deal_card_to_player(deck, curr_player, list(hands.values()))
                    
                    # Wait 1.5 seconds so players can read the draw text before the screen is cleared
                    import time
                    time.sleep(1.5)
                    
                    if curr_player.status == "flipped7":
                        print(f"\n[System] {curr_player.name} flipped 7 during deal phase! Round ends immediately.")
                        input("\nPress Enter to continue...")
                        round_ended_early = True
                        break
                        
            active_count = len([p for p in hands.values() if p.status == "active"])
            if active_count == 0:
                clear_screen_and_show_status(round_number, dealer_name, deck, hands)
                print("\n[System] All players have busted or frozen during deal phase. Round ends.")
                input("\nPress Enter to continue...")
                round_ended_early = True
                break
                
        # 2. Turn-Taking Phase (only if round didn't end early)
        if not round_ended_early:
            print("\n--- Turn-Taking Phase ---")
            current_turn_idx = (dealer_idx + 1) % len(player_names)
            
            while True:
                active_players = [p for p in hands.values() if p.status == "active"]
                if not active_players:
                    print("\n[System] No active players left. Round ends.")
                    break
                    
                if any(p.status == "flipped7" for p in hands.values()):
                    break
                    
                curr_player = hands[player_names[current_turn_idx]]
                
                if curr_player.status == "active":
                    clear_screen_and_show_status(round_number, dealer_name, deck, hands)
                    print(f"It is {curr_player.name}'s turn.")
                    
                    while True:
                        choice = input(f"{curr_player.name}, do you want to [H]it or [S]tay? ").strip().lower()
                        if choice in ['h', 'hit']:
                            deal_card_to_player(deck, curr_player, list(hands.values()))
                            input("\nPress Enter to continue...")
                            break
                        elif choice in ['s', 'stay']:
                            curr_player.status = "stay"
                            print(f"  --> {curr_player.name} chose to Stay.")
                            input("\nPress Enter to continue...")
                            break
                        print("Invalid input. Please enter 'h'/'hit' or 's'/'stay'.")
                        
                    if curr_player.status == "flipped7":
                        break
                        
                current_turn_idx = (current_turn_idx + 1) % len(player_names)
                
        # 3. Round End, Scoring, and Leaderboard Update
        clear_screen_and_show_status(round_number, dealer_name, deck, hands)
        print("--- End of Round Summary ---")
        
        round_scores = {name: calculate_hand_value(hand) for name, hand in hands.items()}
        leaderboard.update_scores(round_scores)
        leaderboard.print_leaderboard(round_scores)
        input("Press Enter to start the next round...")
        
        # 4. Clean up hands and move cards to discards
        for hand in hands.values():
            deck.discards.extend(hand.cards)
            deck.discards.extend(hand.specialcards)
            hand.cards = []
            hand.specialcards = []
            hand.value = 0
            hand.status = "active"
            
        # 5. Check game win condition
        winners = [name for name, score in leaderboard.scores.items() if score >= 200]
        if winners:
            highest_score = max(leaderboard.scores.values())
            highest_players = [name for name, score in leaderboard.scores.items() if score == highest_score]
            
            print("\n" + "=" * 65)
            print("                           GAME OVER!")
            print("=" * 65)
            if len(highest_players) == 1:
                print(f"🎉 Winner is {highest_players[0]} with {highest_score} points! 🎉")
            else:
                print(f"🎉 Tie between {', '.join(highest_players)} with {highest_score} points! 🎉")
            print("=" * 65 + "\n")
            break
            
        # 6. Rotate dealer leftwards (clockwise, meaning dealer_idx += 1)
        dealer_idx = (dealer_idx + 1) % len(player_names)
        round_number += 1


if __name__ == "__main__":
    main()
