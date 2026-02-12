prompt :-

i saw when 1 script is selected which has 2 user but i saw user spwan on both script

solution:-

User class weights are dynamically updated - only active scenarios have weight 1, inactive have weight 0
Locust spawns only users for active scenarios - users won't be spawned for inactive scenario classes
The task checks remain as a safety backup - even spawned users won't execute if their scenario isn't active

