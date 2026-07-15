# ExoDossier — The Plain-English Companion

*A zero-jargon, zero-math walk-through of the same ideas in the main `STUDY_GUIDE.md`. This is
its friendly twin, not a replacement. The technical guide is precise; this one is here to make
sure every idea in it actually lands before you ever have to say it out loud. Whenever I introduce
a real term astronomers use, I'll flag it so you can jump back to the technical guide and follow
the conversation in a room full of experts.*

---

## 1. The 3-minute version

Start with the big picture, because everything else hangs off it.

An **exoplanet** is just a planet that orbits some *other* star — not our Sun. "Exo" means
"outside," so it's a planet outside our own solar system. Picture every star you see at night as a
distant streetlight, and somewhere around a few of those lights there are planets. We can't visit
them, we can't really even *see* them, and yet we've cataloged thousands. How? That's the whole
story below.

Here's the thing that makes finding them so hard: a planet is tiny, dark, and sitting right next
to something blindingly bright — its star. It's like trying to spot a gnat crawling on a
lighthouse lamp from an airplane miles away. The gnat gives off no light of its own, and the lamp
is so bright it washes out everything nearby. So for almost all exoplanets, **we never see the
planet at all.** We watch the *star* very carefully and catch the planet's shadow as it passes.

Now, what does the ExoDossier project actually *do*? It doesn't discover planets with a new
telescope. It fixes a paperwork disaster. Different groups of scientists, using different
telescopes over different decades, have written down conflicting facts about the same planets and
the same stars — one catalog says a planet is a certain size, another disagrees; one even
disagrees about whether the thing is a planet at all. Nobody keeps a clean, running, "who said
what and when" record. **ExoDossier builds exactly that record**, re-checks the raw evidence
itself, and has AI assistants write up a clear, sourced "case file" for each unconfirmed planet —
laying out the evidence for and against it being real.

**The one bridge you need to remember: one engine, two skies.** You already built a machine almost
exactly like this — but pointed at satellites. Your satellite project took messy, contradictory
records about orbiting objects from sources that disagreed, figured out which records were about
the *same* satellite, and kept a careful trail of who claimed what. ExoDossier is that identical
machine, aimed at a different sky: the satellites became stars and planets, the disagreeing
databases became astronomy catalogs, and the "who said what" trail stayed exactly the same idea.
You're not learning a new craft. You're repointing one you already own.

---

## 2. How do you even see a planet trillions of miles away?

Short answer: **you mostly don't.** You watch the star and wait for the planet to get in the way.

Here's the mental picture. Imagine a bright streetlight far down the road, and a moth flying
laps around it. You're too far away to ever see the moth itself. But every time the moth passes
*directly between you and the bulb*, it blocks a sliver of the light, and the streetlight looks
the tiniest bit dimmer for a moment. You never see the moth — you only see the light flicker. Do
that with a star and a planet, and you've just discovered an exoplanet.

Astronomers call that pass-in-front-of-the-star event a **transit**. The planet *transits* its
star. This is, by a huge margin, how most known exoplanets were found, and it's the only method
ExoDossier deals with — so it's worth really getting.

To catch a transit, you track the star's brightness minute by minute and plot it out. That plot —
brightness going up and down, time going across — is called a **light curve.** Think of it like a
heart-rate monitor for a star: a wiggly line showing how bright the star is at every moment. Most
of the time the line is roughly flat. But when a planet transits, the line briefly droops down and
comes back up. That little droop is called the **dip.** A transit *is* a dip in the light curve.
When you hear "we found a dip," it means the star briefly got dimmer as if something crossed in
front of it.

Two beautiful things fall out of that dip almost for free:

**The depth of the dip tells you how big the planet is.** A bigger planet blocks more light, so
it makes a deeper dip. Hold your hand up to a flashlight: your whole palm blocks a lot of light,
one finger blocks a little. Same idea. A planet the size of Jupiter passing a Sun-like star blocks
about 1 out of every 100 units of the star's light — a 1% dip, which is actually pretty easy to
catch. But an Earth-sized planet crossing that same star blocks only about 84 units out of a
*million* — a fantastically tiny flicker. That's why finding small, Earth-like planets is so
brutally hard: the dip is almost too faint to trust. (Astronomers call this dip depth the
**transit depth.** You don't need the equation — just remember deeper dip means bigger planet.)

**The timing of the dips tells you the orbit.** If the star dims, brightens, and then dims again
by the same amount at a regular rhythm, you can measure the time between dips. That gap is how
long the planet takes to circle its star once — its year. Astronomers call it the **orbital
period**, or just the **period.** It's like standing at a bus stop: once you see the same bus pass
twice, you know how often it comes around.

And that's the catch — **you really want to see the dip happen more than once.** One lone dip
could be almost anything: a cosmic-ray hit on the camera, a hiccup in the star, a random glitch.
But if the exact same dip repeats on a steady clockwork rhythm, that's the signature of a planet
loyally orbiting on a schedule. Repetition is what turns "huh, weird flicker" into "there's
something orbiting there." (Hold onto this — it becomes a big deal later, because some real
planets take so long to orbit that we only ever catch *one* transit, and that's a genuine
headache.)

**The other detection methods, one plain sentence each** (so you're not blindsided if someone
mentions them):

- **Radial velocity** — the star *wobbles*. A planet's gravity tugs its star back and forth a
  little, like a big dog on a leash yanking its owner side to side; we detect that tiny wobble.
  This is how most transit candidates get *proven* later, and it needs scarce, expensive telescope
  time.
- **Direct imaging** — we actually *photograph* the planet, by blocking the star's glare like
  holding your thumb up to cover the Sun. Only works for a few big, hot, young planets far from
  their star. Rare and spectacular.
- **Microlensing** — a star passing in front of a more distant star acts like a magnifying glass,
  and a planet around the near star adds a little extra blip. Great for catching faraway planets.
- **Astrometry** — instead of measuring brightness, we measure the star physically shifting its
  position in the sky as the planet tugs it, like watching someone sway while carrying a heavy
  bag. Barely productive yet, but coming.

The takeaway: **transit is king, and transit is our entire world.** Everything ExoDossier touches
started as a dip in a light curve.

---

## 3. Why this is really, really hard

If it were as simple as "watch for a dip," this would be a solved problem. It is emphatically not,
for three reasons.

**Reason one: the star flickers on its own.** Stars are not steady lightbulbs. They have their own
storms, spots, and pulses that make their brightness wobble up and down all the time. On a light
curve, that natural wobble can be *far* bigger than a planet's dip. So before you can spot a
planet's tiny droop, you have to filter out the star's own restlessness first — otherwise it
drowns the planet out completely. It's like trying to hear someone whisper across a room while
music is blaring; you have to turn the music down first. (Astronomers call this clean-up step
**detrending** — removing the slow, natural wiggles so the sharp little transit stands out.)

**Reason two: the instruments drift.** The telescope is a machine floating in space. It jitters,
it heats and cools, it fires little thrusters, cosmic rays smack the camera — all of which shows up
in the light curve as fake wiggles and spikes. So some "dips" are really just the camera having a
bad moment: the equipment equivalent of a smudge on the lens.

**Reason three, the big one: most dips aren't planets at all.** This is the heartbreaker. You
find a lovely, repeating, planet-shaped dip, you get excited... and it turns out to be something
else entirely wearing a planet costume. These impostors are called **false positives**, and
weeding them out is most of the actual work. Astronomers call that weeding-out process
**vetting** — think of a detective ruling suspects out one by one until only the real culprit is
left. Here are the usual impostors:

- **Eclipsing binary** — this is the arch-villain. Sometimes what looks like "one star with a
  planet crossing it" is actually *two stars* orbiting each other, taking turns partially blocking
  one another. When the dimmer star slides in front of the brighter one, the light dips — and it
  looks a lot like a planet transit. But it's not a planet at all; it's a second star. Picture two
  people slow-dancing in front of a lamp, each one periodically eclipsing the other. There are
  clever tells that give it away (for example, two stars usually block *way* more light than a
  planet ever could, and often you can catch a second, smaller dip when the fainter star goes
  behind the brighter one), but you have to go looking for them. This is the single most common way
  a "discovery" turns out to be a dud.

- **Background blends** — sometimes there's a faint pair of eclipsing stars sitting *behind* or
  right *next to* your target star in the sky, and their light leaks into the same patch of camera
  pixels. Their dips get mixed into your star's light curve, making your innocent star look like it
  has a planet. It's like someone else's shadow drifting into the edge of your photo — the flicker
  is real, but it's coming from the wrong object.

- **Instrument noise** — as above, the camera glitches can, now and then, fake a dip all by
  themselves.

- **Star-spots** — stars get dark blotches on their surface, the same way our Sun gets sunspots.
  As the star spins, a big spot rotates into view and the star dims a bit, then brightens as the
  spot rotates away. That can masquerade as a repeating dip, but it's just the star's own freckles
  turning past, not a planet.

So the honest reality is: a raw dip is a *lead*, not a discovery. The whole reason "vetting"
exists as a serious discipline is that the sky is full of things that flicker like planets but
aren't. Keep that in your pocket — it's the motivation for basically everything ExoDossier does.

---

## 4. The telescopes and the data

Where do all these light curves come from? A handful of space telescopes, and — crucially for
you — the data they produce is **free and public.** That last fact is the entire opportunity, so
let's build up to it.

**TESS** (say it "tess") is the workhorse doing the finding right now. It's a space telescope whose
whole job is to stare at big patches of sky and measure the brightness of the stars in them,
watching for dips. Think of it as a wide-angle security camera in space, slowly panning across the
whole sky one patch at a time. Each patch it stares at for about a month is called a **sector.**
TESS finishes one sector, swings to the next, and works its way around the sky — and it's still
happily running today, healthy, cranking out new sectors. So there's a constant firehose of fresh
light curves pouring in with nobody having looked at most of them yet.

**Kepler** was TESS's predecessor — the pioneer. Instead of panning around, Kepler pointed at *one*
single patch of sky and stared at it for years, and it found the first huge haul of exoplanets. It
finished its mission a while back, but its data is still gold: because so many of Kepler's planets
were later checked and settled, its records serve as a giant answer key. When you want to test
whether your own method gets the right answer, you run it against Kepler's known cases and see if
you agree.

**"The data is public and free" — why that's the whole game.** Every light curve TESS and Kepler
ever recorded is posted online for anyone to download, no cost, no permission needed, small enough
to work with on a laptop. That means an individual with a good idea can get their hands on the
exact same raw material as any professional observatory. The bottleneck was never *access* to the
data — it's what you *do* with it. That's the crack in the door that lets an outsider walk in.
(The main download library is called **MAST**; the free software tool everyone uses to pull and
poke at the light curves is a Python package called **lightkurve.** Names to recognize, nothing to
memorize.)

**Gaia** (say it "guy-uh") plays a totally different but essential role: it's the cosmic census.
Gaia is a mission that carefully measured the *stars* themselves — how far away each one is, how
big, how hot, how bright. Think of it as the town records office for the galaxy: it doesn't find
planets, but it tells you the vital statistics of every star a planet might orbit. And that matters
enormously, because — remember from section 2 — a dip only tells you the planet's size *relative
to its star.* If you don't know the star's true size, you don't know the planet's true size. Get
the star wrong and every planet around it comes out wrong. Gaia is what keeps the stars honest.

**The archives — the shared spreadsheets everyone uses.** Once a planet or candidate is found, it
gets logged in big public databases that the whole field treats as the common reference. Two names
to know: the **NASA Exoplanet Archive** (the closest thing to an official master list) and
**ExoFOP** (a shared workspace where people post follow-up notes and observations about candidates).
Picture them as giant communal spreadsheets that everyone reads from and adds to. As you'll see in
section 6, those spreadsheets don't always agree with each other — and that disagreement is
exactly where ExoDossier lives.

---

## 5. How planets get 'found' today — the assembly line

Going from "a dip in a light curve" to "a confirmed planet in the textbooks" is an assembly line
with several stages. Understanding the stages — and especially one key distinction in the middle —
is what makes you sound like you actually know the field.

Here's the line, in plain steps:

1. **A dip is spotted.** Software combs through millions of light curves looking for repeating
   dips. A dip that's strong enough to be worth a second look gets flagged automatically.

2. **It becomes a candidate.** Human reviewers look at the promising flagged dips and promote the
   good ones to an official candidate list. A candidate on the TESS list is called a **TOI** —
   a "TESS Object of Interest." A TOI is basically a *suspect*: something worth investigating that
   has not yet been proven to be a planet.

3. **It gets vetted.** The candidate goes through the impostor checks from section 3 — is it
   secretly two stars? a background blend? a glitch? Automated tools score how likely it is to be
   real versus fake.

4. **Real telescopes follow up.** For the survivors, astronomers point other telescopes at the
   star to gather more evidence — especially to catch the star's *wobble* (radial velocity),
   because that reveals the planet's mass and clinches the case. This step is the true bottleneck:
   there are far more candidates than there is telescope time to check them.

5. **It gets confirmed.** Once the evidence is solid, the object graduates to a **confirmed
   planet** and goes in the record books.

Now, **the one distinction you must get right: candidate versus confirmed.** A *candidate* is a
suspect — a promising dip that could still turn out to be an eclipsing binary or a glitch. A
*confirmed* planet is one where the evidence is strong enough that scientists stake their names on
it. Mixing these two up is the fastest way to out yourself as a tourist: "we found a candidate" and
"we found a planet" are wildly different claims. (The pros make an even finer split between
"validated" — statistically almost-certainly real — and "confirmed" — actually weighed via the
wobble — but candidate-versus-confirmed is the one that matters for you.)

Here's the part that creates the whole opportunity: **there is an enormous backlog of candidates
that nobody has had time to fully check.** The finding machines spit out suspects far faster than
humans and telescopes can work through them. Thousands of candidates sit in limbo, half-examined,
waiting for someone to build the full case. The pile keeps growing.

**And outsiders genuinely can contribute.** This isn't a closed priesthood. There's a whole
citizen-science lane where hobbyists — people with no astronomy degree — hunt through public light
curves by eye and have found *real, credited planets.* The most famous effort is called **Planet
Hunters**, where volunteers eyeball light curves and catch dips the automated software threw away.
They've flagged candidates that became official, some of which became confirmed planets, with the
volunteers named as co-authors. The lesson: eagle-eyed outsiders have a real, proven track record
here. The door is open.

---

## 6. The mess we specialize in

Now we get to the specific problem ExoDossier attacks — and it's not a physics problem, it's a
*bookkeeping* problem, which is exactly why your background fits.

Remember those shared spreadsheets from section 4? Here's the dirty secret: **they disagree with
each other about the same objects.** Different scientists measured different things at different
times with different instruments, wrote down their answers, and nobody keeps a clean running tally
of who said what. So for one single planet, you can find:

- One catalog saying it's a certain size, another saying it's noticeably bigger or smaller.
- One catalog listing the star as one temperature, another listing it differently.
- And — most alarming — the catalogs sometimes disagree about whether the object is *even a
  planet at all* versus a likely false positive.

This isn't sloppiness by dumb people. It's the natural result of many careful teams working
independently over years, each measuring a piece, with no shared "master record" tying it all
together and no note of which value came from where. It's like five people keeping separate
address books for the same friend, each with a slightly different phone number, and no way to tell
which one is current.

Two concrete examples from ExoDossier's very first day of pulling the data — these are the hooks
you can actually quote:

**Example one: 3,274 candidates where the catalogs can't agree on the basic question.** On day one,
just by lining the databases up side by side, the project found over three thousand candidates
where different sources disagree about whether the thing is even a real planet. Three *thousand*
open disputes, sitting there unreconciled — a backlog of genuine confusion nobody had tallied.

**Example two: TRAPPIST-1 with the wrong star temperature.** TRAPPIST-1 is one of the most famous
systems in all of exoplanet science — a small, cool red star with *seven* rocky planets around it,
several possibly in the life-friendly zone. It's a poster child, studied endlessly. And yet one
catalog was carrying a *wrong, default placeholder* temperature for the star — a stand-in value
somebody never replaced with the real measurement. If it can happen to TRAPPIST-1, the most
scrutinized system on the board, it's happening all over the place.

**Why does a wrong star temperature actually matter?** Because of a chain reaction. The star's
temperature decides where its **habitable zone** is — the "just right" band of orbits where a
planet could have liquid water. (It's literally nicknamed the Goldilocks zone: not too hot, not too
cold.) A cooler star has its cozy zone tucked in close; a hotter star pushes it farther out. So if
you record the temperature wrong, you draw the Goldilocks zone in the wrong place — and a planet
actually sitting in the life-friendly band might get labeled "too hot," or vice versa. Get the star
wrong, and you get the single most exciting question about the planet — *could it host life?* —
wrong too. The bad bookkeeping isn't cosmetic; it quietly corrupts the science.

That's the mess. Nobody owns a clean, sourced, "who-said-what" running record of it. That's the
gap.

---

## 7. What ExoDossier actually does, in plain words

So here's the project, in four moves. Keep the detective metaphor going — ExoDossier is basically
a very disciplined investigator building airtight case files.

**(a) It untangles which records are the same object, and tracks who said what.** The same star
shows up under a dozen different ID numbers across different catalogs (TESS gave it one name,
Kepler another, Gaia another, older surveys others still). ExoDossier figures out which of those
scattered entries are all secretly the *same* physical star or planet, and stitches them into one
record — but crucially, instead of blending the conflicting values into mush, it *keeps every
value and labels its source.* "Catalog A says the radius is this; Catalog B says that; here's where
each came from." Astronomers would call this tracking the **provenance** — think of it as a
fact-checker's citations, a receipt attached to every single number so you can always trace it back
to who claimed it. That "keep the conflict and cite it" move is the heart of the whole thing.

**(b) It re-checks the light curves itself.** Rather than trusting what a catalog says a dip looks
like, ExoDossier goes back to the original raw brightness data and re-derives the transit
independently — its own fresh measurement, not a copy of someone else's. That way, when two
catalogs disagree, there's an independent third opinion made from scratch.

**(c) AI assistants write a clear, sourced 'case file' for each candidate.** This is the
centerpiece and where the project gets its name. For each unconfirmed candidate, AI assistants
assemble everything — the light-curve evidence, the catalog cross-checks, the warning signs, the
relevant past research — into a single readable **dossier**: a case file laying out the evidence
*for* and *against* this being a real planet, every claim cited back to its source, with a stated
level of confidence. Today a human wanting that full picture has to hunt down all those scattered
pieces by hand, every time. The dossier does it automatically and shows its work.

**(d) It keeps score.** This is what separates it from a toy. ExoDossier takes cases where the
*answer is already known* — planets everyone agrees are real, and impostors everyone agrees are
fake — and checks how often its own dossiers reach the right verdict. That produces an honest,
published accuracy number. Anyone can build something that *sounds* confident; almost nobody can
say "and here's my measured track record against known answers." That scorekeeping is the
credibility.

**Now, the equally important part — what ExoDossier does NOT claim.** It does *not* confirm
planets. It does *not* own a telescope. It is *not* trying to out-astronomer the astronomers or
build a better dip-finder. It makes the *evidence* better and the *to-do list* smarter — helping
decide which candidates deserve the scarce telescope time, and handing follow-up teams a
ready-made case file. Being crisp about that boundary is a feature, not a weakness: it's what makes
the whole pitch believable instead of hype. When someone worries you're overclaiming, this
boundary is your answer.

**And the "MCP server," in plain words.** You'll see "MCP server" in the technical spec and it
sounds like intimidating plumbing. All it means: **a way for an AI assistant to look a planet up
and instantly get back the sourced case file.** Picture a front desk that an AI can walk up to and
ask, "give me everything on candidate so-and-so," and get the whole dossier — evidence, sources,
conflicts, confidence — handed over on the spot. It's the delivery window for the case files.

---

## 8. Why nobody's done this, and why you can

The obvious question anyone will ask: if this is so useful, why hasn't someone already built it?

The honest answer is that the field has poured its energy into the two stages that feel like the
"real science": the *finding* (spotting dips) and the *scoring* (rating how likely a candidate is
real). Both are being automated hard by well-funded teams who are good at it. That part of the
assembly line is crowded and fast-moving.

But there's a step everyone quietly skips past: **writing up the full, sourced case for each
candidate is still done slowly, by hand, one at a time, by whoever has the patience.** The scoring
tools give you a *number*; they don't give you the assembled *file* — the cited evidence for and
against, the catalog conflicts laid bare, the source on every value. That assembly is tedious,
unglamorous, and un-automated. It's a genuine gap, not a solved problem someone forgot to mention.

**And here's your unfair advantage.** You have already built exactly this kind of machine — an
evidence-and-provenance system that reconciles disagreeing catalogs, tracks who-said-what, and
proves its own accuracy against known answers — just for satellites instead of stars. The hard,
transferable skill was never the astronomy or the code that proposes a match; it's the *discipline
of proving the merged record is right and keeping the receipts.* That's the part almost nobody in
astronomy treats as a first-class problem, and it's the part you've done before. You're not
bluffing your way into a new field — you're bringing a tool the field didn't know it was missing.

---

## 9. A mini-glossary

Quick-scan reference — each term in one plain sentence with its analogy. Alphabetical.

- **Astrometry** — finding a planet by watching its star physically shift position in the sky, like
  spotting someone sway while holding a heavy bag.
- **Background blend** — a faint pair of stars behind or beside your target whose light leaks in and
  fakes a dip, like a stranger's shadow drifting into the edge of your photo.
- **Candidate** — a suspect: a dip promising enough to investigate but not yet proven to be a
  planet.
- **Confirmed planet** — a candidate proven real enough that scientists stake their names on it; the
  opposite of a mere suspect.
- **Detrending** — filtering out the star's own natural flickering so the planet's tiny dip can be
  seen, like turning down loud music to hear a whisper.
- **Direct imaging** — actually photographing a planet by blocking its star's glare, like using your
  thumb to cover the Sun.
- **Dip** — the small drop in a star's brightness when a planet crosses in front; the flicker you're
  hunting for.
- **Dossier** — the assembled case file for one candidate: all the evidence for and against, with
  every claim cited, like a detective's binder.
- **Eclipsing binary** — two stars taking turns partly blocking each other, faking a planet's dip;
  the most common impostor, like two dancers passing in front of a lamp.
- **ExoFOP** — a shared online workspace where people post follow-up notes on candidates; one of the
  communal spreadsheets everyone uses.
- **Exoplanet** — a planet orbiting a star other than our Sun, out among the distant "streetlights."
- **False positive** — any dip that looks like a planet but isn't; the thing vetting exists to catch.
- **Gaia** — the mission that measured the stars' own vital statistics (distance, size, temperature);
  the galaxy's census office.
- **Habitable zone** — the "just right" band of orbits where liquid water could exist; the Goldilocks
  zone, not too hot, not too cold.
- **Kepler** — TESS's predecessor telescope that stared at one patch of sky for years; now a trusted
  answer key of settled cases.
- **Light curve** — a graph of a star's brightness over time; a heart-rate monitor for the star.
- **lightkurve** — the free software tool everyone uses to download and examine light curves.
- **MAST** — the free public library where all the telescope data lives for anyone to download.
- **MCP server** — a front desk that lets an AI assistant instantly request and receive a
  candidate's case file.
- **Microlensing** — using a passing star as a magnifying glass to reveal a planet by a brief extra
  brightening.
- **NASA Exoplanet Archive** — the closest thing to the official master list of known planets and
  candidates.
- **Period** — how long a planet takes to circle its star once (its year), measured from the gap
  between repeating dips.
- **Planet Hunters** — a citizen-science project where hobbyists eyeball light curves and have found
  real, credited planets.
- **Provenance** — the "who said what, and where it came from" trail attached to every value; a
  receipt for each fact.
- **Radial velocity** — detecting a planet by the wobble its gravity gives the star, like a dog on a
  leash tugging its owner.
- **Sector** — one patch of sky that TESS stares at for about a month before moving on; one frame of
  its sky-wide panorama.
- **Star-spot** — a dark blotch on a star (like a sunspot) that can fake a dip as the star rotates,
  like a freckle turning past.
- **TESS** — the space telescope currently panning across the whole sky, patch by patch, hunting for
  dips.
- **TOI** — "TESS Object of Interest," the official label for a TESS candidate (a suspect on the
  list).
- **Transit** — a planet crossing in front of its star and dimming it slightly, like a moth passing a
  distant streetlight.
- **Transit depth** — how deep the dip is, which reveals the planet's size; a bigger object blocks
  more light, like a palm versus a finger over a flashlight.
- **Vetting** — the detective work of ruling out impostors until only a believable planet is left.

---

## 10. "If someone asks you..."

Six things an astronomer, an interviewer, or a curious friend might throw at you — and how to
answer plainly and honestly, without faking expertise you don't have.

**"So you found a planet?"**
> "No — and I'm careful about that. I don't find planets or confirm them; I don't have a telescope.
> What I built is the thing that assembles the *case* for each candidate someone else found — all
> the scattered evidence, pulled together, sourced, and laid out so a human can judge it. I'm the
> one who builds the file, not the one who makes the discovery."

**"How is this different from the tools that already score candidates?"**
> "Those tools give you a *number* — how likely a candidate is to be real. Useful, and I use their
> output. But a number doesn't tell you *why*, or *according to whom*, or *how sure*. I build the
> assembled case: the evidence for and against, every claim cited back to its source, the catalog
> disagreements shown instead of hidden. A score tells you what; my dossier tells you why."

**"You're not an astronomer — why should anyone trust your work here?"**
> "Correct, I'm not, and I don't pretend to be — I won't out-argue an astrophysicist on physics.
> What I bring is what the downstream mess actually needs: I've built systems twice that reconcile
> messy, contradictory databases and *prove* the merged record is right, with a published accuracy
> number. That discipline is the hard, transferable part, and it's exactly what's missing here."

**"Isn't this just an AI writing some text?"**
> "The flashy demo is; the real product isn't. Anyone can prompt an AI to write nice-sounding
> prose. What can't be faked in a weekend is the sourced record that keeps every catalog conflict
> instead of hiding it, an independent re-check of the raw light curves, and a measured accuracy
> score against known answers. The AI is the glue; the discipline underneath is the value."

**"Why does this matter — isn't astronomy already super precise?"**
> "The *measurements* are precise; the *bookkeeping* isn't. The same star wears a dozen different ID
> numbers, and the catalogs disagree about the same planet's size — sometimes about whether it's
> even a planet. And it's not trivial: get a star's temperature wrong and you can misjudge whether
> its planet is in the life-friendly zone. I fix the bookkeeping so those judgments rest on
> traceable facts."

**"What would success actually look like in a few months?"**
> "A live, public site with case files for the neglected candidates nobody's had time to work
> through, each showing its own re-checked evidence and cited sources — plus an honest, published
> accuracy number you can check, and at least one real astronomer or group actually using it.
> Something you can browse, a number you can verify, and one real collaboration started."

---

*This is the friendly on-ramp. Once these ten ideas feel natural, open `STUDY_GUIDE.md` — the same
concepts are waiting there in their precise, expert form, and you'll find you already understand
them.*
