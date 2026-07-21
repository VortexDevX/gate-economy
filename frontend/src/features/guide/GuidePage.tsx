import {
  AlertTriangle,
  Aperture,
  ArrowRight,
  Coins,
  Compass,
  Crown,
  Hourglass,
  Landmark,
  Shield,
  TrendingUp,
} from "lucide-react";
import { Link } from "react-router-dom";
import { GameAction, GamePanel, PanelHeading, ScreenHeader } from "../../components/game/GameUI";

const glossary = [
  ["World cycle", "The heartbeat of the game. Queued actions resolve and active gates produce income when a cycle completes."],
  ["Gate share", "A slice of ownership in one gate. Shares can earn yield and can be traded until the gate collapses."],
  ["Offering", "A newly discovered gate that is not producing income yet. It activates after its launch period or enough initial shares sell."],
  ["Stability", "The gate's remaining safety. Lower stability means greater collapse danger. Each rank has its own collapse line."],
  ["Yield / cycle", "The coin an active gate is expected to distribute every completed world cycle."],
  ["Mark price", "The best current estimate of a share's market value, based on trades and the visible order book."],
  ["Locked coin", "Money reserved by an open buy order. It is still yours, but cannot be spent twice."],
  ["Intent", "A command waiting for the next world cycle. In the interface, these appear as queued actions or results."],
];

export default function GuidePage() {
  return (
    <div className="game-page guide-page">
      <ScreenHeader
        eyebrow="Hunter field manual"
        title="How the Obsidian Exchange works"
        description="No combat stats. No hidden quest chain. You are building wealth by discovering, owning, and escaping volatile magical assets."
        action={<GameAction to="/discover">Start with an expedition</GameAction>}
      />

      <GamePanel className="guide-premise" accent="gold">
        <div className="guide-premise-sigil"><Aperture size={54} aria-hidden="true" /></div>
        <div>
          <span className="game-eyebrow">The one-sentence version</span>
          <h2>Own gates while they earn. Leave before they die.</h2>
          <p>
            Every dungeon gate is a temporary income-producing asset. Its shares can pay you each cycle,
            but falling stability can make the entire gate collapse and erase the remaining value.
          </p>
        </div>
      </GamePanel>

      <section className="guide-journey" aria-labelledby="journey-title">
        <div className="guide-section-title">
          <span>01</span>
          <div><h2 id="journey-title">Your first ten minutes</h2><p>Follow this exact path on a new account.</p></div>
        </div>
        <div className="guide-step-grid">
          <GuideStep number="1" icon={<Compass />} title="Scout an E-rank gate" copy="You begin with ¤10. An E-rank expedition costs ¤0.10, making it the safest first command." action="Open Expeditions" to="/discover" />
          <GuideStep number="2" icon={<Hourglass />} title="Wait for a world cycle" copy="Commands are queued. When the next cycle resolves, discovery either succeeds or is rejected with a reason." action="Open Action Queue" to="/orders" />
          <GuideStep number="3" icon={<Landmark />} title="Inspect your finder stake" copy="A successful player discovery grants 10% of the new gate's shares. New gates begin in Offering." action="Open Gate Atlas" to="/gates" />
          <GuideStep number="4" icon={<TrendingUp />} title="Earn, trade, then exit" copy="Active gates pay every cycle. Watch the stability line and sell before collapse destroys the gate." action="Open Chronicle" to="/profile" />
        </div>
      </section>

      <section className="guide-risk-grid">
        <GamePanel accent="good">
          <PanelHeading title="How you make coin" />
          <ul className="guide-rule-list">
            <li><Coins size={18} /><div><strong>Finder stake</strong><span>Successful discoveries give you initial ownership.</span></div></li>
            <li><TrendingUp size={18} /><div><strong>Gate yield</strong><span>Active gate shares distribute income on completed cycles.</span></div></li>
            <li><Landmark size={18} /><div><strong>Trading gains</strong><span>Buy shares at one price and sell to another player later.</span></div></li>
            <li><Crown size={18} /><div><strong>Guild dividends</strong><span>Later, guild ownership can distribute treasury profits.</span></div></li>
          </ul>
        </GamePanel>
        <GamePanel accent="danger">
          <PanelHeading title="How you lose coin" />
          <ul className="guide-rule-list guide-rule-list-danger">
            <li><AlertTriangle size={18} /><div><strong>Gate collapse</strong><span>Collapsed shares become worthless and trading closes permanently.</span></div></li>
            <li><Hourglass size={18} /><div><strong>Bad timing</strong><span>Offering gates do not earn yet; unstable gates also stop producing yield.</span></div></li>
            <li><Coins size={18} /><div><strong>Fees and escrow</strong><span>Orders include fees, while open bids temporarily lock your coin.</span></div></li>
            <li><Shield size={18} /><div><strong>Concentration</strong><span>Putting everything into one gate magnifies a single collapse.</span></div></li>
          </ul>
        </GamePanel>
      </section>

      <section className="guide-glossary" aria-labelledby="glossary-title">
        <div className="guide-section-title">
          <span>02</span>
          <div><h2 id="glossary-title">Plain-language glossary</h2><p>The terms you will see around the exchange.</p></div>
        </div>
        <div className="glossary-grid">
          {glossary.map(([term, definition]) => (
            <details key={term} className="glossary-item">
              <summary>{term}<span aria-hidden="true">+</span></summary>
              <p>{definition}</p>
            </details>
          ))}
        </div>
      </section>

      <GamePanel className="guide-guild-unlock" accent="violet">
        <div className="guide-guild-icon"><Shield size={34} aria-hidden="true" /></div>
        <div>
          <span className="game-eyebrow">Later-game milestone</span>
          <h2>Guild founding costs ¤50</h2>
          <p>You start with ¤10, so a guild is a progression goal—not your first task. Grow through gates first.</p>
        </div>
        <GameAction to="/guilds" tone="secondary">Visit Guild Hall</GameAction>
      </GamePanel>
    </div>
  );
}

function GuideStep({ number, icon, title, copy, action, to }: { number: string; icon: React.ReactElement; title: string; copy: string; action: string; to: string }) {
  return (
    <article className="guide-step">
      <div className="guide-step-number">{number}</div>
      <div className="guide-step-icon">{icon}</div>
      <h3>{title}</h3>
      <p>{copy}</p>
      <Link to={to}>{action} <ArrowRight size={14} aria-hidden="true" /></Link>
    </article>
  );
}
