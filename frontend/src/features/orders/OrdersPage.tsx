import { useState, type ReactElement } from "react";
import { Link } from "react-router-dom";
import {
  CheckCircle2,
  CircleX,
  Coins,
  Hourglass,
  ListChecks,
  ReceiptText,
  RotateCcw,
  Scale,
  ShieldAlert,
} from "lucide-react";
import type { IntentResponse, OrderResponse } from "../../api/types";
import {
  GameAction,
  GameButton,
  GameEmpty,
  GamePanel,
  PanelHeading,
  PlainTip,
  ScreenHeader,
  StatRune,
} from "../../components/game/GameUI";
import ErrorAlert from "../../components/ErrorAlert";
import LoadingSpinner from "../../components/LoadingSpinner";
import Pagination from "../../components/Pagination";
import { useMyIntents, useMyOrders, useSubmitIntent } from "../../hooks/queries";
import { formatCurrency, shortId } from "../../utils/format";

const PAGE_SIZE = 20;

export default function OrdersPage() {
  const [page, setPage] = useState(1);
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState("");
  const [actionError, setActionError] = useState("");
  const offset = (page - 1) * PAGE_SIZE;
  const ordersQuery = useMyOrders({ limit: PAGE_SIZE, offset });
  const intentsQuery = useMyIntents({ limit: 10, offset: 0 });
  const cancelIntent = useSubmitIntent();

  const orders = ordersQuery.data?.orders ?? [];
  const intents = intentsQuery.data?.items ?? [];
  const totalPages = ordersQuery.data
    ? Math.ceil(ordersQuery.data.total / PAGE_SIZE)
    : 0;
  const waitingActions = intents.filter((intent) =>
    intent.status === "QUEUED" || intent.status === "PROCESSING",
  );
  const activeOrders = orders.filter((order) =>
    order.status === "OPEN" || order.status === "PARTIAL",
  );
  const lockedCoin = activeOrders.reduce(
    (sum, order) => sum + order.escrow_micro,
    0,
  );
  const filledShares = orders.reduce(
    (sum, order) => sum + order.filled_quantity,
    0,
  );

  const handleCancel = async (orderId: string) => {
    setCancellingId(orderId);
    setActionMessage("");
    setActionError("");
    try {
      await cancelIntent.mutateAsync({
        intent_type: "CANCEL_ORDER",
        payload: { order_id: orderId },
      });
      setActionMessage(
        "Cancellation requested. The order closes when the next world cycle resolves.",
      );
      setTimeout(() => ordersQuery.refetch(), 1_000);
    } catch {
      setActionError(
        "The cancellation could not be queued. The order is still active.",
      );
    } finally {
      setCancellingId(null);
    }
  };

  return (
    <div className="game-page orders-game-page">
      <ScreenHeader
        eyebrow="Action ledger · Commands and trades"
        title="Orders & Results"
        description="Every command enters the world here. First it waits for a cycle; then it either completes, fails with a reason, or remains on the market waiting for another trader."
        action={<GameAction to="/gates">Find a gate to trade</GameAction>}
      />

      <section className="orders-game-stats" aria-label="Action summary">
        <StatRune
          label="Waiting for a cycle"
          value={String(waitingActions.length)}
          note="Commands the world has not resolved yet"
          tone={waitingActions.length ? "aether" : "muted"}
          icon={<Hourglass size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Orders still open"
          value={String(activeOrders.length)}
          note="These stay listed until matched or cancelled"
          tone={activeOrders.length ? "warn" : "muted"}
          icon={<Scale size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Coin committed here"
          value={`¤ ${formatCurrency(lockedCoin)}`}
          note="Reserved by open buy orders shown on this page"
          tone={lockedCoin ? "gold" : "muted"}
          icon={<Coins size={18} aria-hidden="true" />}
        />
        <StatRune
          label="Shares matched"
          value={String(filledShares)}
          note="Total fills shown on this page"
          tone={filledShares ? "good" : "muted"}
          icon={<ListChecks size={18} aria-hidden="true" />}
        />
      </section>

      <GamePanel className="orders-game-explainer" accent="violet">
        <PanelHeading
          title="What happens after you click?"
          detail="The exchange is cycle-based, so a submitted action is not an instant result."
        />
        <ol className="orders-game-flow">
          <FlowStep
            number="1"
            icon={<ReceiptText />}
            title="Command queued"
            copy="The server accepts your instruction and holds it for the next cycle."
          />
          <FlowStep
            number="2"
            icon={<RotateCcw />}
            title="World resolves"
            copy="Funds, ownership, and rules are checked by the game engine."
          />
          <FlowStep
            number="3"
            icon={<CheckCircle2 />}
            title="Result recorded"
            copy="Completed trades appear below; failures always include a reason."
          />
        </ol>
      </GamePanel>

      {(actionMessage || actionError) && (
        <div
          className={`orders-game-receipt ${actionError ? "orders-game-receipt-danger" : "orders-game-receipt-good"}`}
          role={actionError ? "alert" : "status"}
        >
          {actionError ? <ShieldAlert size={18} aria-hidden="true" /> : <CheckCircle2 size={18} aria-hidden="true" />}
          <span>{actionError || actionMessage}</span>
        </div>
      )}

      <section className="orders-game-grid">
        <GamePanel className="orders-game-commands" accent="aether">
          <PanelHeading
            title="Recent commands"
            detail="Your newest instructions and their final outcome."
            action={intentsQuery.data && (
              <span className="orders-game-count">{intentsQuery.data.total} total</span>
            )}
          />
          {intentsQuery.isLoading && <LoadingSpinner />}
          {intentsQuery.error && (
            <ErrorAlert message="Your recent commands could not be read. They remain safely recorded by the server." />
          )}
          {!intentsQuery.isLoading && !intentsQuery.error && intents.length === 0 && (
            <GameEmpty
              title="No commands issued"
              message="Scout a gate or place a trade. Your command and its result will appear here."
              action={{ to: "/discover", label: "Launch your first expedition" }}
            />
          )}
          {intents.length > 0 && (
            <ol className="orders-game-command-list" aria-label="Recent command results">
              {intents.map((intent) => (
                <CommandReceipt key={intent.id} intent={intent} />
              ))}
            </ol>
          )}
        </GamePanel>

        <GamePanel className="orders-game-market" accent="gold">
          <PanelHeading
            title="Market orders"
            detail="A completed command can create an order that waits for a matching buyer or seller."
            action={ordersQuery.data && (
              <span className="orders-game-count">{ordersQuery.data.total} total</span>
            )}
          />
          <PlainTip>
            Open does not mean failed. It means your price is still waiting for another trader to accept it.
          </PlainTip>
          {ordersQuery.isLoading && <LoadingSpinner />}
          {ordersQuery.error && (
            <ErrorAlert message="Market orders are temporarily unavailable. No order was changed." />
          )}
          {!ordersQuery.isLoading && !ordersQuery.error && orders.length === 0 && (
            <GameEmpty
              title="No market orders yet"
              message="Open a gate, choose Buy or Sell, and review the exact cost before placing an order."
              action={{ to: "/gates", label: "Browse the Gate Atlas" }}
            />
          )}
          {orders.length > 0 && (
            <div className="orders-game-order-list">
              {orders.map((order) => (
                <OrderCard
                  key={order.id}
                  order={order}
                  cancelling={cancellingId === order.id}
                  onCancel={() => handleCancel(order.id)}
                />
              ))}
            </div>
          )}
          {totalPages > 1 && (
            <Pagination
              currentPage={page}
              totalPages={totalPages}
              onPageChange={setPage}
            />
          )}
        </GamePanel>
      </section>
    </div>
  );
}

function FlowStep({
  number,
  icon,
  title,
  copy,
}: {
  number: string;
  icon: ReactElement;
  title: string;
  copy: string;
}) {
  return (
    <li className="orders-game-flow-step">
      <span className="orders-game-flow-icon">{icon}</span>
      <span className="orders-game-flow-number">{number}</span>
      <div>
        <h3>{title}</h3>
        <p>{copy}</p>
      </div>
    </li>
  );
}

function CommandReceipt({ intent }: { intent: IntentResponse }) {
  const presentation = intentPresentation(intent);
  return (
    <li className={`orders-game-command orders-game-command-${presentation.tone}`}>
      <span className="orders-game-command-icon">{presentation.icon}</span>
      <div className="orders-game-command-copy">
        <div className="orders-game-command-title">
          <h3>{plainIntentName(intent.intent_type)}</h3>
          <span className={`orders-game-status orders-game-status-${presentation.tone}`}>
            {presentation.label}
          </span>
        </div>
        <p>{presentation.copy}</p>
        {intent.reject_reason && (
          <div className="orders-game-reject" role="alert">
            {intent.reject_reason}
          </div>
        )}
        <span className="orders-game-command-meta">
          Command {shortId(intent.id)}
          {intent.processed_tick != null ? ` · resolved in cycle ${intent.processed_tick}` : ""}
        </span>
      </div>
    </li>
  );
}

function OrderCard({
  order,
  cancelling,
  onCancel,
}: {
  order: OrderResponse;
  cancelling: boolean;
  onCancel: () => void;
}) {
  const canCancel = order.status === "OPEN" || order.status === "PARTIAL";
  const remaining = Math.max(order.quantity - order.filled_quantity, 0);
  const destination = order.asset_type === "GATE_SHARE"
    ? `/gates/${order.asset_id}`
    : `/guilds/${order.asset_id}`;
  const assetKind = order.asset_type === "GATE_SHARE" ? "Gate shares" : "Guild shares";
  const side = order.side === "BUY" ? "Buying" : "Selling";

  return (
    <article className={`orders-game-order orders-game-order-${order.side.toLowerCase()}`}>
      <div className="orders-game-order-head">
        <div>
          <span className="orders-game-side">{side}</span>
          <h3>{assetKind} · {shortId(order.asset_id)}</h3>
        </div>
        <span className={`orders-game-status orders-game-status-${orderTone(order.status)}`}>
          {plainOrderStatus(order.status)}
        </span>
      </div>
      <div className="orders-game-order-economy">
        <div><span>Price per share</span><strong>¤ {formatCurrency(order.price_limit_micro)}</strong></div>
        <div><span>Requested</span><strong>{order.quantity}</strong></div>
        <div><span>Still waiting</span><strong>{remaining}</strong></div>
        <div><span>Coin locked</span><strong>{order.escrow_micro > 0 ? `¤ ${formatCurrency(order.escrow_micro)}` : "None"}</strong></div>
      </div>
      <div className="orders-game-fill">
        <div><span>Fill progress</span><strong>{order.filled_quantity} of {order.quantity}</strong></div>
        <progress value={order.filled_quantity} max={Math.max(order.quantity, 1)}>
          {order.filled_quantity} of {order.quantity}
        </progress>
      </div>
      <div className="orders-game-order-foot">
        <span>Placed in cycle {order.created_at_tick}</span>
        <div className="orders-game-order-actions">
          <Link to={destination} className="orders-game-inspect">Inspect asset</Link>
          {canCancel && (
            <GameButton tone="danger" disabled={cancelling} onClick={onCancel}>
              {cancelling ? "Queueing…" : "Cancel order"}
            </GameButton>
          )}
        </div>
      </div>
    </article>
  );
}

function intentPresentation(intent: IntentResponse): {
  label: string;
  copy: string;
  tone: "waiting" | "good" | "danger";
  icon: ReactElement;
} {
  if (intent.status === "REJECTED") {
    return {
      label: "Could not complete",
      copy: "The world rejected this command. Read the reason below before trying again.",
      tone: "danger",
      icon: <CircleX aria-hidden="true" />,
    };
  }
  if (intent.status === "EXECUTED") {
    return {
      label: "Completed",
      copy: "The world accepted this command and applied its result.",
      tone: "good",
      icon: <CheckCircle2 aria-hidden="true" />,
    };
  }
  return {
    label: intent.status === "PROCESSING" ? "Resolving now" : "Waiting for cycle",
    copy: "This command is safely queued and has not changed your holdings yet.",
    tone: "waiting",
    icon: <Hourglass aria-hidden="true" />,
  };
}

function plainIntentName(intentType: string): string {
  const names: Record<string, string> = {
    DISCOVER_GATE: "Scout a new gate",
    PLACE_ORDER: "Place a market order",
    CANCEL_ORDER: "Cancel a market order",
    CREATE_GUILD: "Found a guild",
    FOUND_GUILD: "Found a guild",
    ISSUE_DIVIDEND: "Distribute guild coin",
    GUILD_INVEST_GATE: "Invest guild coin in a gate",
  };
  return names[intentType] ?? sentenceCase(intentType);
}

function plainOrderStatus(status: string): string {
  const labels: Record<string, string> = {
    OPEN: "Waiting for a match",
    PARTIAL: "Partly matched",
    FILLED: "Fully matched",
    CANCELLED: "Closed",
  };
  return labels[status] ?? sentenceCase(status);
}

function orderTone(status: string): "waiting" | "good" | "muted" {
  if (status === "FILLED") return "good";
  if (status === "OPEN" || status === "PARTIAL") return "waiting";
  return "muted";
}

function sentenceCase(value: string): string {
  const text = value.replace(/_/g, " ").toLowerCase();
  return text ? text[0].toUpperCase() + text.slice(1) : value;
}
