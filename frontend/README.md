# LACUNA frontend

The Stage 12 product interface is a counterfactual evidence laboratory, not a generic contract explorer. It reads the canonical StudioNet deployment at `0x5abdf6380Faaa1f0Eb51cc666A8660D5a8Dd73a6` using the exact schema snapshot in `../docs/deployed-schema.json`.

## Visual system

LACUNA uses an *alternate-trajectory observatory* palette:

- **Night field** `#081310` for the unknown counterfactual world.
- **Evidence green** `#b8e785` for locked evidence, expected trajectories, and confirmed protocol progress.
- **Forensic teal** `#0d201b` / `#2b4940` for records and evidence surfaces.
- **Divergence amber** `#e7b374` for actual outcomes against an expected range.
- **Caution coral** `#ffae9a` for validation and transaction errors.

The range band is deliberately textual and accessible: it has an ARIA label and an equivalent data table. BPS are translated to percentages in record and verdict displays; forms describe the required integer input format.

## Development

```sh
cp .env.example .env
npm install
npm run dev
```

`npm run verify:live` performs read-only StudioNet checks. Contract writes require a real injected wallet on StudioNet and are successful only after the GenLayer receipt is `FINALIZED` with `FINISHED_WITH_RETURN`.

The interface never seeds agreements, evidence, baselines, verdicts, settlements, or transactions. A fresh contract is intentionally rendered with guided empty states.
