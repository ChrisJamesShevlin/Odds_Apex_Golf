import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
import re

P_FLOOR = 0.02
EDGE_THRESHOLD_WEAK = 15
EDGE_THRESHOLD_MEDIUM = 25
EDGE_THRESHOLD_STRONG = 35

def calculate_lays():
    output_txt.delete("1.0", tk.END)
    lines = input_txt.get("1.0", tk.END).strip().splitlines()

    try:
        bank = float(balance_entry.get())
        if bank <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Input Error", "Please enter a positive number for your account balance.")
        return

    all_players = []
    lay_candidates = []
    signal_groups = {"Strong": [], "Medium": [], "Weak": []}
    cap_factors = {"Strong": 0.10, "Medium": 0.075, "Weak": 0.05}

    for line in lines:
        if "|" not in line or "LiveOdds" not in line:
            continue
        try:
            name_part, stats = line.split("|", 1)
            name = name_part.strip()

            m_mod  = re.search(r"Model[:%]?\s*([0-9]+(?:\.[0-9]+)?)%", stats)
            m_odds = re.search(r"LiveOdds[:]?[\s]*([0-9]+(?:\.[0-9]+)?)", stats)
            m_edge = re.search(r"Edge:\s*[+-]?([0-9]+(?:\.[0-9]+)?)%", stats)
            m_ev   = re.search(r"EV:\s*[+-]?([0-9]+(?:\.[0-9]+)?)", stats)

            if not (m_mod and m_odds and m_edge and m_ev):
                continue

            p_model = max(float(m_mod.group(1)) / 100.0, P_FLOOR)
            live_odds = float(m_odds.group(1))
            edge_pct = float(m_edge.group(1))
            ev_value = float(m_ev.group(1))

            if live_odds <= 1:
                continue

            all_players.append({
                "name": name,
                "model_prob": p_model,
                "live_odds": live_odds,
                "edge": edge_pct,
                "ev": ev_value
            })

        except Exception:
            continue

    model_order = sorted(all_players, key=lambda x: x["model_prob"], reverse=True)
    market_order = sorted(all_players, key=lambda x: x["live_odds"])

    for p in all_players:
        model_rank = next((i + 1 for i, x in enumerate(model_order) if x["name"] == p["name"]), None)
        market_rank = next((i + 1 for i, x in enumerate(market_order) if x["name"] == p["name"]), None)
        rank_delta = model_rank - market_rank
        signal = ""

        if market_rank < model_rank:
            edge = p["edge"]
            if rank_delta >= 3 and edge >= EDGE_THRESHOLD_STRONG:
                signal = "Strong"
            elif rank_delta >= 2 and edge >= EDGE_THRESHOLD_MEDIUM:
                signal = "Medium"
            elif rank_delta >= 1 and edge >= EDGE_THRESHOLD_WEAK:
                signal = "Weak"

            if signal:
                signal_groups[signal].append({
                    "name": p["name"],
                    "model_rank": model_rank,
                    "market_rank": market_rank,
                    "live_odds": p["live_odds"],
                    "edge": edge,
                    "ev": p["ev"],
                    "signal": signal
                })

    # EV-based stake allocation within signal groups
    for signal_strength, players in signal_groups.items():
        if not players:
            continue

        max_liability_per_player = cap_factors[signal_strength] * bank
        total_ev = sum(p['ev'] for p in players)

        for p in players:
            ev_weight = p['ev'] / total_ev if total_ev > 0 else 0
            allocated_liability = ev_weight * len(players) * max_liability_per_player
            stake = allocated_liability / (p["live_odds"] - 1)

            lay_candidates.append({
                "name": p["name"],
                "model_rank": p["model_rank"],
                "market_rank": p["market_rank"],
                "ev": p["ev"],
                "signal": p["signal"],
                "stake": stake,
                "liability": allocated_liability
            })

    # Output
    output_txt.insert(tk.END, f"{'Name':<15} {'Model Rank':<12} {'Market Rank':<13} {'EV':<8} {'Stake (£)':<10} {'Liability (£)':<15} {'Signal'}\n")
    output_txt.insert(tk.END, "-" * 110 + "\n")

    for p in lay_candidates:
        output_txt.insert(
            tk.END,
            f"{p['name']:<15} {p['model_rank']:<12} {p['market_rank']:<13} {p['ev']:<8.3f} £{p['stake']:<9.2f} £{p['liability']:<14.2f} {p['signal']}\n"
        )

# GUI setup
root = tk.Tk()
root.title("Lay Opportunity Table")

tk.Label(root, text="Paste your model output here:")\
    .grid(row=0, column=0, sticky="w", padx=4, pady=4)
input_txt = ScrolledText(root, width=95, height=8)
input_txt.grid(row=1, column=0, columnspan=2, padx=4)

tk.Label(root, text="Account balance (£):")\
    .grid(row=2, column=0, sticky="w", padx=4, pady=(10,2))
balance_entry = tk.Entry(root)
balance_entry.grid(row=2, column=1, sticky="w", padx=4)

tk.Button(root, text="Calculate Lays", command=calculate_lays)\
    .grid(row=3, column=0, columnspan=2, pady=8)

output_txt = ScrolledText(root, width=95, height=20)
output_txt.grid(row=4, column=0, columnspan=2, padx=4, pady=(0,8))

root.mainloop()
