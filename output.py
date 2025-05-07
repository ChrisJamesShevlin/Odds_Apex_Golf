import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
import re

P_FLOOR = 0.02
MAX_FAIR = 50.0

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

    cap_liability = 0.10 * bank
    all_players = []

    for line in lines:
        if "|" not in line or "LiveOdds" not in line:
            continue
        try:
            name_part, stats = line.split("|", 1)
            name = name_part.strip()

            m_mod  = re.search(r"Model[:%]?\s*([0-9]+(?:\.[0-9]+)?)%", stats)
            m_odds = re.search(r"LiveOdds[:]?[\s]*([0-9]+(?:\.[0-9]+)?)", stats)
            m_edge = re.search(r"Edge:\s*[+-]?([0-9]+(?:\.[0-9]+)?)%", stats)

            if not (m_mod and m_odds and m_edge):
                continue

            p_model = max(float(m_mod.group(1)) / 100.0, P_FLOOR)
            live_odds = float(m_odds.group(1))
            edge_pct = float(m_edge.group(1))  # Already positive number

            if live_odds <= 1:
                continue

            stake = cap_liability / (live_odds - 1)

            all_players.append({
                "name": name,
                "model_prob": p_model,
                "live_odds": live_odds,
                "stake_raw": stake,
                "edge": edge_pct
            })
        except Exception:
            continue

    model_order = sorted(all_players, key=lambda x: x["model_prob"], reverse=True)
    market_order = sorted(all_players, key=lambda x: x["live_odds"])

    output_txt.insert(tk.END, f"{'Name':<15} {'Model Rank':<12} {'Market Rank':<13} {'Stake (£)':<10} {'Signal'}\n")
    output_txt.insert(tk.END, "-" * 75 + "\n")

    for p in all_players:
        model_rank = next((i + 1 for i, x in enumerate(model_order) if x["name"] == p["name"]), None)
        market_rank = next((i + 1 for i, x in enumerate(market_order) if x["name"] == p["name"]), None)
        rank_delta = model_rank - market_rank

        signal = ""
        stake = 0.00

        if market_rank < model_rank:
            stake = p["stake_raw"]
            edge = p["edge"]

            if rank_delta >= 3 and edge >= 35:
                signal = "Lay Mispricing (Strong)"
            elif rank_delta >= 2 and edge >= 25:
                signal = "Lay Mispricing (Medium)"
            elif rank_delta >= 1 and edge >= 15:
                signal = "Lay Mispricing (Weak)"

        output_txt.insert(
            tk.END,
            f"{p['name']:<15} {model_rank:<12} {market_rank:<13} £{stake:<9.2f} {signal}\n"
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
