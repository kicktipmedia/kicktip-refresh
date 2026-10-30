"""Team alias dictionary for the question parser (138 FBS teams). Source of truth: TABLE below (full name :: school :: mascot :: extra aliases).
build() returns {"map": {normalized alias: [team index, ...]}, "ask": [alias, ...]} where
  - an alias that maps to more than one team is ambiguous (parser asks which one);
  - an alias in `ask` is always treated as ambiguous even if it maps to one team (Utah is asked: Utah / Utah State / Utah Tech).
  - "nonfbs": aliases of teams the model does not simulate (Utah Tech): parser answers 'not modeled'.
Normalization (shared with src/web/parse.js): lowercase, strip accents and apostrophes, '&' -> ' and ', other punctuation -> space, collapse spaces."""
import re, unicodedata

def norm(s):
    s = unicodedata.normalize("NFD", s); s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    s = s.replace("&", " and ").replace("'", "").replace("\u2019", "")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip()

TABLE = """
UTSA Roadrunners :: UTSA :: Roadrunners :: texas san antonio;ut san antonio;the roadrunners
Memphis Tigers :: Memphis :: Tigers :: memphis tigers
South Florida Bulls :: South Florida :: Bulls :: usf;s florida;south florida bulls
North Texas Mean Green :: North Texas :: Mean Green :: unt;north texas
Army Black Knights :: Army :: Black Knights :: west point;cadets;army west point
Florida Atlantic Owls :: Florida Atlantic :: Owls :: fau;florida atl
UAB Blazers :: UAB :: Blazers :: alabama birmingham;uab
Tulsa Golden Hurricane :: Tulsa :: Golden Hurricane :: tulsa
Tulane Green Wave :: Tulane :: Green Wave :: tulane
East Carolina Pirates :: East Carolina :: Pirates :: ecu;e carolina
Navy Midshipmen :: Navy :: Midshipmen :: mids
Temple Owls :: Temple :: Owls :: temple
Charlotte 49ers :: Charlotte :: 49ers :: niners;forty niners
Rice Owls :: Rice :: Owls :: rice
Miami Hurricanes :: Miami FL :: Hurricanes :: miami florida;miami fl;miami (fl);the u;canes;the canes;um miami;hurricanes
Wake Forest Demon Deacons :: Wake Forest :: Demon Deacons :: wake;deacs;wfu;demon deacs
SMU Mustangs :: SMU :: Mustangs :: southern methodist;ponies
Pittsburgh Panthers :: Pittsburgh :: Panthers :: pitt;pittsburgh pitt
Virginia Tech Hokies :: Virginia Tech :: Hokies :: vt;vtech;va tech;virginia polytechnic
Clemson Tigers :: Clemson :: Tigers :: clemson
North Carolina Tar Heels :: North Carolina :: Tar Heels :: unc;tarheels;carolina tar heels;n carolina;north carolina tar heels
Duke Blue Devils :: Duke :: Blue Devils :: duke
Louisville Cardinals :: Louisville :: Cardinals :: lville;uofl;the ville
Virginia Cavaliers :: Virginia :: Cavaliers :: uva;wahoos;hoos;cavs
Boston College Eagles :: Boston College :: Eagles :: bc;b c
NC State Wolfpack :: NC State :: Wolfpack :: north carolina state;n c state;ncsu;nc st
California Golden Bears :: California :: Golden Bears :: cal;cal bears;golden bears;uc berkeley;berkeley
Florida State Seminoles :: Florida State :: Seminoles :: fsu;noles;seminoles
Stanford Cardinal :: Stanford :: Cardinal :: stanford
Georgia Tech Yellow Jackets :: Georgia Tech :: Yellow Jackets :: gt;gatech;ga tech;ramblin wreck;jackets
Syracuse Orange :: Syracuse :: Orange :: cuse;syr
BYU Cougars :: BYU :: Cougars :: brigham young;byu cougars
Texas Tech Red Raiders :: Texas Tech :: Red Raiders :: ttu;tech red raiders;raiders
Utah Utes :: Utah :: Utes :: the utes;university of utah;utah utes
Houston Cougars :: Houston :: Cougars :: uh;coogs
Arizona Wildcats :: Arizona :: Wildcats :: u of a;arizona wildcats
Baylor Bears :: Baylor :: Bears :: baylor
Oklahoma State Cowboys :: Oklahoma State :: Cowboys :: okst;ok state;okla state;pokes
Cincinnati Bearcats :: Cincinnati :: Bearcats :: cincy;cincinatti;bearcats
Kansas State Wildcats :: Kansas State :: Wildcats :: k state;ksu;kstate;kansas st;k-state
West Virginia Mountaineers :: West Virginia :: Mountaineers :: wvu;w virginia;wv
UCF Knights :: UCF :: Knights :: central florida;ucf
Arizona State Sun Devils :: Arizona State :: Sun Devils :: asu;az state;sun devils;arizona st
Iowa State Cyclones :: Iowa State :: Cyclones :: isu;cyclones;iowa st
TCU Horned Frogs :: TCU :: Horned Frogs :: texas christian;frogs;horned frogs
Colorado Buffaloes :: Colorado :: Buffaloes :: cu;buffs;colorado buffs;cu boulder
Kansas Jayhawks :: Kansas :: Jayhawks :: ku;jayhawks
UCLA Bruins :: UCLA :: Bruins :: bruins
Ohio State Buckeyes :: Ohio State :: Buckeyes :: tosu;ohio st;buckeyes;the ohio state
Indiana Hoosiers :: Indiana :: Hoosiers :: iu;hoosiers
USC Trojans :: USC :: Trojans :: southern cal;southern california;usc trojans
Iowa Hawkeyes :: Iowa :: Hawkeyes :: hawkeyes
Northwestern Wildcats :: Northwestern :: Wildcats :: nu;northwestern
Nebraska Cornhuskers :: Nebraska :: Cornhuskers :: huskers;nu huskers;cornhuskers
Minnesota Golden Gophers :: Minnesota :: Golden Gophers :: gophers;goldy;golden gophers
Oregon Ducks :: Oregon :: Ducks :: ducks;uo
Wisconsin Badgers :: Wisconsin :: Badgers :: uw madison;badgers;wisco
Michigan Wolverines :: Michigan :: Wolverines :: umich;wolverines
Washington Huskies :: Washington :: Huskies :: uw;udub;washington huskies;uw huskies
Illinois Fighting Illini :: Illinois :: Fighting Illini :: illini;uiuc;fighting illini
Purdue Boilermakers :: Purdue :: Boilermakers :: boilermakers;boilers
Penn State Nittany Lions :: Penn State :: Nittany Lions :: psu;penn st;nittany lions;the nittany lions
Rutgers Scarlet Knights :: Rutgers :: Scarlet Knights :: scarlet knights
Maryland Terrapins :: Maryland :: Terrapins :: terps;umd;terrapins
Michigan State Spartans :: Michigan State :: Spartans :: msu;mich state;michigan st;sparty
Liberty Flames :: Liberty :: Flames :: flames
Jacksonville State Gamecocks :: Jacksonville State :: Gamecocks :: jax state;jsu;jacksonville st
Middle Tennessee Blue Raiders :: Middle Tennessee :: Blue Raiders :: mtsu;middle tennessee state;blue raiders
New Mexico State Aggies :: New Mexico State :: Aggies :: nmsu;new mexico st;nm state
Western Kentucky Hilltoppers :: Western Kentucky :: Hilltoppers :: wku;toppers;hilltoppers;western ky
Delaware Blue Hens :: Delaware :: Blue Hens :: blue hens;ud;udel
Florida International Panthers :: Florida International :: Panthers :: fiu;fla international
Missouri State Bears :: Missouri State :: Bears :: msu;missouri st;mo state
Kennesaw State Owls :: Kennesaw State :: Owls :: kennesaw;ksu owls;kennesaw st
Sam Houston Bearkats :: Sam Houston :: Bearkats :: shsu;sam houston state;bearkats
Notre Dame Fighting Irish :: Notre Dame :: Fighting Irish :: nd;irish;the irish;fighting irish
UConn Huskies :: UConn :: Huskies :: connecticut;uconn huskies;uconn
Ohio Bobcats :: Ohio :: Bobcats :: ohio university;ou bobcats;bobcats
Western Michigan Broncos :: Western Michigan :: Broncos :: wmu;w michigan;wmich
Toledo Rockets :: Toledo :: Rockets :: rockets
Buffalo Bulls :: Buffalo :: Bulls :: ub;buffalo bulls
Miami (OH) RedHawks :: Miami OH :: RedHawks :: miami ohio;miami of ohio;miami (oh);miami oh;redhawks;miami redhawks;moh
Massachusetts Minutemen :: Massachusetts :: Minutemen :: umass;minutemen
Eastern Michigan Eagles :: Eastern Michigan :: Eagles :: emu;e michigan;eastern mich
Central Michigan Chippewas :: Central Michigan :: Chippewas :: cmu;c michigan;chips;central mich
Bowling Green Falcons :: Bowling Green :: Falcons :: bgsu;bowling green state
Kent State Golden Flashes :: Kent State :: Golden Flashes :: kent;golden flashes;kent st
Ball State Cardinals :: Ball State :: Cardinals :: bsu cardinals;ball st
Akron Zips :: Akron :: Zips :: zips
Sacramento State Hornets :: Sacramento State :: Hornets :: sac state;sacramento st;hornets
North Dakota State Bison :: North Dakota State :: Bison :: ndsu;north dakota st;the bison;bison
New Mexico Lobos :: New Mexico :: Lobos :: unm;lobos
Air Force Falcons :: Air Force :: Falcons :: afa;air force academy
Wyoming Cowboys :: Wyoming :: Cowboys :: wyo;pokes wyoming
San José State Spartans :: San Jose State :: Spartans :: sjsu;san jose st;sjsu spartans
UNLV Rebels :: UNLV :: Rebels :: las vegas;nevada las vegas;unlv rebels
Nevada Wolf Pack :: Nevada :: Wolf Pack :: wolfpack nevada;unr;nevada wolf pack
UTEP Miners :: UTEP :: Miners :: texas el paso;miners
Hawai'i Rainbow Warriors :: Hawaii :: Rainbow Warriors :: hawai i;rainbow warriors;uh hawaii
Northern Illinois Huskies :: Northern Illinois :: Huskies :: niu;northern ill;n illinois
Boise State Broncos :: Boise State :: Broncos :: boise;bsu;boise st;the blue turf
Oregon State Beavers :: Oregon State :: Beavers :: beavs;beavers;oregon st
Fresno State Bulldogs :: Fresno State :: Bulldogs :: fresno;fresno st
Texas State Bobcats :: Texas State :: Bobcats :: txst;texas st;tx state
San Diego State Aztecs :: San Diego State :: Aztecs :: sdsu;san diego st;aztecs
Utah State Aggies :: Utah State :: Aggies :: usu;utah st;utah state aggies
Colorado State Rams :: Colorado State :: Rams :: csu rams;colorado st;csu;rams
Washington State Cougars :: Washington State :: Cougars :: wsu;wazzu;wash state;washington st;cougs
Georgia Bulldogs :: Georgia :: Bulldogs :: uga;dawgs;georgia bulldogs;uga dawgs
Kentucky Wildcats :: Kentucky :: Wildcats :: uk;kentucky;big blue
Tennessee Volunteers :: Tennessee :: Volunteers :: vols;ut vols;volunteers;tennessee vols
Ole Miss Rebels :: Ole Miss :: Rebels :: university of mississippi;olemiss;ole miss rebels
Alabama Crimson Tide :: Alabama :: Crimson Tide :: bama;crimson tide;roll tide;tide;the tide
Florida Gators :: Florida :: Gators :: gators;uf;florida gators
LSU Tigers :: LSU :: Tigers :: louisiana state;lsu tigers;geaux tigers
Missouri Tigers :: Missouri :: Tigers :: mizzou;mizz;mu tigers
Mississippi State Bulldogs :: Mississippi State :: Bulldogs :: msu;miss state;msst;mississippi st;state bulldogs
Auburn Tigers :: Auburn :: Tigers :: war eagle;au tigers
Texas Longhorns :: Texas :: Longhorns :: ut;longhorns;hook em;texas longhorns;ut austin
Texas A&M Aggies :: Texas A&M :: Aggies :: tamu;a and m;aggies texas;texas a and m;aggs;tx a and m
Oklahoma Sooners :: Oklahoma :: Sooners :: ou;sooners;boomer sooner
South Carolina Gamecocks :: South Carolina :: Gamecocks :: s carolina;scar;sc gamecocks;south carolina gamecocks
Arkansas Razorbacks :: Arkansas :: Razorbacks :: hogs;razorbacks;the hogs;woo pig
Vanderbilt Commodores :: Vanderbilt :: Commodores :: vandy;dores;commodores
James Madison Dukes :: James Madison :: Dukes :: jmu;dukes
App State Mountaineers :: App State :: Mountaineers :: appalachian state;appalachian;app st;appstate;app state mountaineers
Georgia State Panthers :: Georgia State :: Panthers :: gsu;ga state;georgia st
Marshall Thundering Herd :: Marshall :: Thundering Herd :: thundering herd;herd
Georgia Southern Eagles :: Georgia Southern :: Eagles :: gsu eagles;ga southern;georgia so
Coastal Carolina Chanticleers :: Coastal Carolina :: Chanticleers :: ccu;coastal;chanticleers;chants
Old Dominion Monarchs :: Old Dominion :: Monarchs :: odu;monarchs
Louisiana Ragin' Cajuns :: Louisiana :: Ragin' Cajuns :: ull;ragin cajuns;louisiana lafayette;ul lafayette;cajuns;ul;louisiana cajuns
Louisiana Tech Bulldogs :: Louisiana Tech :: Bulldogs :: la tech;latech
South Alabama Jaguars :: South Alabama :: Jaguars :: usa jaguars;s alabama;jaguars;south al
Troy Trojans :: Troy :: Trojans :: troy trojans
Arkansas State Red Wolves :: Arkansas State :: Red Wolves :: astate;a state;arkansas st;red wolves
Southern Miss Golden Eagles :: Southern Miss :: Golden Eagles :: southern mississippi;usm;golden eagles;smu southern miss
UL Monroe Warhawks :: UL Monroe :: Warhawks :: ulm;louisiana monroe;la monroe;warhawks
"""
# Aliases that must ALWAYS trigger a clarification question (even when they match exactly one team).
ASK = ["utah", "miami", "louisiana", "carolina", "osu", "mississippi"]
# Aliases that name teams the model does NOT simulate (non-FBS). Parser says 'not modeled' instead of guessing.
NONFBS = ["utah tech", "utah tech trailblazers", "southern utah", "weber state", "idaho state", "montana", "montana state", "northern arizona", "fcs"]
# Extra deliberate ambiguity groups (alias -> full names it can mean), in addition to automatic collisions.
EXTRA = {"utah": ["Utah Utes", "Utah State Aggies"], "miami": ["Miami Hurricanes", "Miami (OH) RedHawks"], "louisiana": ["Louisiana Ragin' Cajuns", "UL Monroe Warhawks", "Louisiana Tech Bulldogs", "LSU Tigers"],
         "carolina": ["North Carolina Tar Heels", "South Carolina Gamecocks", "Coastal Carolina Chanticleers", "East Carolina Pirates"],
         "osu": ["Ohio State Buckeyes", "Oklahoma State Cowboys", "Oregon State Beavers"], "mississippi": ["Ole Miss Rebels", "Mississippi State Bulldogs"]}

def parse_table():
    rows = []
    for ln in TABLE.strip().splitlines():
        full, school, mascot, extra = [x.strip() for x in ln.split("::")]
        rows.append((full, school, mascot, [e for e in extra.split(";") if e.strip()]))
    return rows

def build(names, conf_of, fcs):
    """names: list indexed by team index (FCS last). Returns {"map","ask","nonfbs"}."""
    idx = {n: i for i, n in enumerate(names)}; amap = {}
    rows = parse_table(); missing = [n for n in names[:fcs] if n not in {r[0] for r in rows}]
    assert not missing, f"teams without an alias row: {missing}"
    unknown = [r[0] for r in rows if r[0] not in idx]; assert not unknown, f"alias rows for unknown teams: {unknown}"
    def add(a, t):
        a = norm(a)
        if a and t not in amap.setdefault(a, []): amap[a].append(t)
    for full, school, mascot, extra in rows:
        t = idx[full]
        for a in [full, school, school + " " + mascot, mascot] + extra: add(a, t)
    # bare mascots are weak aliases only when unique; handled by the collision rule (>1 team => ambiguous)
    for k, lst in EXTRA.items(): amap[norm(k)] = [idx[x] for x in lst]
    return dict(map={k: sorted(v) for k, v in sorted(amap.items())}, ask=sorted(set(norm(a) for a in ASK[:])), nonfbs=[norm(x) for x in NONFBS])
