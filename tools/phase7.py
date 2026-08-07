import os

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

art_7a = """~~~
   .============================================================.
   |  ROBCO INDUSTRIES (TM) TERMLINK PROTOCOL                   |
   |  =======================================================   |
   |  > AUTHORIZED PERSONNEL ONLY                               |
   |  > TIMING AUTHORITY: LBE-1421 GPSDO                        |
   |  > ATTEMPTS REMAINING: 3                                   |
   |  > HINT: THE PASSWORD IS NOT "hunter2"                     |
   |                                                            |
   |  UNAUTHORIZED ACCESS WILL BE LOGGED, TIMESTAMPED WITH      |
   |  ATOMIC PRECISION, AND MOCKED AT THE NEXT STANDUP.         |
   '============================================================'
~~~
"""

art_7b = """~~~
        ______________________________________________________
       |  CONELRAD  ::  CIVIL DEFENSE RADIO  ::  EST. 1953    |
       |                                                      |
       |   540    640     800    1000    1240    1400  kHz    |
       |    |     (CD)     |       |      (CD)     |          |
       |    |______|_______|_______|_______|_______|          |
       |                                                      |
       |   IN THE EVENT OF ACTUAL ANOMALY, LEAVE THE RF       |
       |   SPECTRUM EXACTLY AS WEIRD AS YOU FOUND IT.         |
       |______________________________________________________|
~~~
"""

art_7c = """~~~
     .-----------------------------------------.
     |  *************************************  |
     |  *              FALLOUT              *  |
     |  *              SHELTER              *  |
     |  *           _____________           *  |
     |  *           \\   |   |   /           *  |
     |  *             \\  |   |  /           *  |
     |  *              \\ |   | /            *  |
     |  *          ----+--+--+----          *  |
     |  *              / |   | \\            *  |
     |  *             /  |   |  \\           *  |
     |  *           /___|___|___\\           *  |
     |  *                                   *  |
     |  *    CAPACITY: 1 GPSDO, 4 NERVES    *  |
     |  *************************************  |
     '-----------------------------------------'
~~~
"""

art_7d = """~~~
          .------------------------.
          |   CD V-700   MODEL 6   |
          |  .------------------.  |
          |  | 0    5    10  50 |  |
          |  | ....A........... |  |
          |  '------------------'  |
          |   (o) ZERO   (===) HV  |
          '----------.  .----------'
                     |  |
                  ___|  |___
                 |  PROBE    |
                 |  goes     |   SPEC-015 RADON STAGING:
                 |  *clicky* |   promotion pending.
                 |___________|   it knows what it did.
~~~
"""

art_7e = """~~~
                , - ~ ~ ~ - ,
            , '       |       ' ,
          ,       \\   |   /       ,
         ,         \\  |  /         ,
         ,   ----.   (o)   .----   ,
         ,         /  |  \\         ,
          ,       /   |   \\       ,
            ,         |         ,
              ' - , _ _ _ ,  '

        KCET-ATLAS COHERENCE ENGINE
     "Splitting hairs, not atoms, since 2026."
~~~
"""

art_7f = """~~~
            _.-^^---....,,--_
        _--                    --_
       <      PHASE COHERENCE     >)
       |       FAILURE, 1954      |
        \\._      (colorized)    _./
           ```--. . , ; .--'''
                 | |   |
              .-=||  | |=-.
              `-=#$%&%$#=-'
                 | ;  :|
        _____.,-#%&$@%#&#~,._____

   THIS IS WHAT TWO NODES DISAGREEING ABOUT TIME LOOKS LIKE.
   LOCK YOUR CLOCKS. DUCK AND COVER IS NOT A TIMING STRATEGY.
~~~
"""

art_7g = """~~~
              D U C K   A N D   C O V E R
                           |
            _______________|_______________
            \\  \\  \\  \\  \\  |  /  /  /  /  /
             \\  \\  \\  \\  \\ | /  /  /  /  /
              \\____________V____________/
                     .-=========-.
                    /   _     _   \\
                   |  (o_o) (o_o)  |
                   |     \\___/     |     BERT THE TURTLE SAYS:
                    \\   .---.     /
                     \\_/       \\_/     WHEN /dev/pps0 VANISHES:
                  ___|           |___    DUCK under the desk,
                 /   \\  .---.   /   \\   COVER the GPSDO,
                |     \\(     ) /     |   grep the journal.
                 \\    | '---' |    /     NOBODY GETS HURT.
                  '---|  | |  |---'
                      |__| |__|
~~~
"""


def insert_after(filepath, text_to_find, insertion):
    if not os.path.exists(filepath):
        print(f"Skipping {filepath}, does not exist")
        return
    with open(filepath, "r") as f:
        content = f.read()
    if insertion in content:
        return
    content = content.replace(text_to_find, text_to_find + "\n\n" + insertion)
    with open(filepath, "w") as f:
        f.write(content)

# 7a
insert_after(os.path.join(repo_root, "SECURITY.md"), "# Security Policy", art_7a)
insert_after(os.path.join(repo_root, "docs/security/HDF5_TAMPER_EVIDENCE_AND_KEY_MANAGEMENT.md"), "# HDF5 Tamper-Evidence and Key Management", art_7a)

# 7b
insert_after(os.path.join(repo_root, "README.md"), "## Waterfall Explained", art_7b)

# 7c
insert_after(os.path.join(repo_root, "README.md"), "## Troubleshooting", art_7c)

# 7d
insert_after(os.path.join(repo_root, "docs/RADONEYE_GATT_MAP.md"), "# RadonEye GATT Map", art_7d)

# 7e
# Place beside cordyceps art or in Scientific justification.
insert_after(os.path.join(repo_root, "README.md"), "## Architecture", art_7e)

# 7f
# Replace the old cloud with the new cloud.
old_cloud = """```text
       _.-^^---....,,--       
   _--                  --_   
  <                        >) 
  |                         | 
   \._                   _./  
      ```--. . , ; .--'''       
            | |   |             
         .-=||  | |=-.   
         `-=#$%&%$#=-'   
            | ;  :|     
   _____.,-#%&$@%#&#~,._____
```"""

readme_path = os.path.join(repo_root, "README.md")
with open(readme_path, "r") as f:
    readme_content = f.read()
if old_cloud in readme_content:
    readme_content = readme_content.replace(old_cloud, art_7f)
    with open(readme_path, "w") as f:
        f.write(readme_content)

# 7g
insert_after(os.path.join(repo_root, "docs/qualification/TIER1_HARDWARE_QUALIFICATION_STANDARD.md"), "# Tier 1 Hardware Qualification Standard", art_7g)

# 7h
# Add one-line deadpan captions under existing section headers
insert_after(os.path.join(repo_root, "README.md"), "### Baseline Learning FSM (SPEC-009)", "*72 hours of learning before it trusts you. The FSM has been hurt before.*")

print("Phase 7 ASCII art injected.")
