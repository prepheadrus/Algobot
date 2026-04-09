with open("core/trading/position_manager.py", "r") as f:
    content = f.read()

# Update _open_position_internal
content = content.replace(
    "                stop_loss=stop_loss,\n                take_profit=take_profit,",
    "                stop_loss=stop_loss,\n                initial_stop_loss=stop_loss,\n                take_profit=take_profit,"
)

# Update size_to_close rounding
content = content.replace(
    "            is_partial_close = size_to_close is not None and size_to_close < position.size",
    "            is_partial_close = size_to_close is not None and round(size_to_close, 4) < round(position.size, 4)\n            if size_to_close is not None:\n                size_to_close = round(size_to_close, 4)"
)

# Replace should_take_partial_profit block
start_idx = content.find("        if position.should_take_partial_profit(current_price):")
if start_idx != -1:
    end_idx = content.find("        # ========================================================================\n        # AŞAMA 2: BAŞA BAŞ (BREAKEVEN) KORUMASI (Kısmi kar alınmamışsa)", start_idx)
    if end_idx != -1:
        replacement = """        triggered_levels = position.get_triggered_tp_levels(current_price)
        if triggered_levels:
            total_percentage = sum(level.get("percentage", 0.0) for level in triggered_levels)
            if total_percentage > 0:
                size_to_close = round(position.size * total_percentage, 4)

                logger.info(
                    f"[RISK] 3 Aşamalı Kâr Koruma - AŞAMA 1 & 2: "
                    f"{position.symbol} {len(triggered_levels)} hedef vuruldu! "
                    f"Fiyat: ${current_price:.2f}, Kapanacak Miktar: {size_to_close}"
                )

                # Update take_profit_levels state synchronously
                new_tp_levels = []
                for level in position.take_profit_levels:
                    new_level = dict(level)
                    for triggered in triggered_levels:
                        if new_level.get("level") == triggered.get("level"):
                            new_level["hit"] = True
                    new_tp_levels.append(new_level)

                breakeven_price = position.entry_price

                # SENKRON STATE GÜNCELLEMESİ (Race Condition Koruması)
                position = dataclasses.replace(
                    position,
                    take_profit_levels=new_tp_levels,
                    stop_loss=breakeven_price,
                    partial_profit_taken=True,
                    breakeven_activated=True
                )
                self.positions[position.bot_id] = position

                # EVENT LOOP ASENKRON ÇAĞRI (State koruması sonrası fırlat)
                asyncio.create_task(
                    self.close_position(
                        bot_id=position.bot_id,
                        exit_price=current_price,
                        reason="partial_tp_hit",
                        size_to_close=size_to_close
                    )
                )

"""
        content = content[:start_idx] + replacement + content[end_idx:]

with open("core/trading/position_manager.py", "w") as f:
    f.write(content)
