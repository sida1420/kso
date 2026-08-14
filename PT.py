import init
import selection
import classes
import evaluate
import random
import numpy as np
import mutation
import crossover
import os
import json
from concurrent.futures import ProcessPoolExecutor


# ─── Worker globals ──────────────────────────────────────────────────────────
_worker_evaluator = None

def _init_worker(layout):
    """Each process builds its own Evaluator so __init__ caches run once."""
    global _worker_evaluator
    _worker_evaluator = evaluate.Evaluator(layout)

def _eval_chunk(chunk):
    """Evaluate a batch of replicas/candidates. Returns list of np vectors."""
    evas = _worker_evaluator.evaluate(chunk)
    return [np.array(list(e.values())) for e in evas]


# ─── Main PT loop ────────────────────────────────────────────────────────────
def run():
    paras = init.Parameters()
    objectives = list(paras.target_metrics.keys())

    min_T = 0.005
    max_T = 0.09
    n_swaps = 11  # Always odd

    layout = classes.Layout()
    mutator = mutation.Mutator(layout)
    decoder = crossover.RKPosDecoder(layout)

    if paras.population_size < 1:
        return

    temperatures = init.init_temperature(paras.population_size, min_T, max_T)
    replicas = init.init(paras.population_size, layout)
    weight_vectors = init.init_weight_vectors(paras.target_metrics, paras.population_size, 50)

    # ─── Multiprocessing setup ───────────────────────────────────────────────
    n_workers = min(os.cpu_count() or 1, paras.population_size)
    # Chunk size: divide population evenly across workers
    chunk_size = max(1, paras.population_size // n_workers)

    def split(pop):
        return [pop[i:i + chunk_size] for i in range(0, len(pop), chunk_size)]

    with ProcessPoolExecutor(
        max_workers=n_workers,
        initializer=_init_worker,
        initargs=(layout,)
    ) as pool:

        # ─── Initial evaluation ──────────────────────────────────────────────
        evaluations = [
            ev for chunk in pool.map(_eval_chunk, split(replicas))
            for ev in chunk
        ]

        dynamic_min = [min(e[i] for e in evaluations) for i in range(len(objectives))]
        dynamic_max = [max(e[i] for e in evaluations) for i in range(len(objectives))]

        scaled_evals = [evaluate.apply_scale(e, dynamic_min, dynamic_max) for e in evaluations]
        scores = [evaluate.weighted_sum_scaled(scaled_evals[i], weight_vectors[i])
                for i in range(paras.population_size)]

        elites = [(scores[0], evaluations[0], replicas[0])]
        num_elites = 5

        total_jump_accept = np.zeros(paras.population_size)
        total_swap_accept = np.zeros(paras.population_size - 1)
        total_better_jumps = np.zeros(paras.population_size)

        range_changed = False
        generation_count = 0
        log_range = 1

        while generation_count < paras.generation_limit:
            generation_count += 1
            if generation_count % log_range == 0 or paras.dev_mode:
                if generation_count >= log_range * 10 and log_range < 100:
                    log_range *= 10
                print(f"\tGENERATION {generation_count}")

            # ─── Generate candidates ───────────────────────────────────────────
            candidates = []
            for i in range(paras.population_size):
                if i < paras.population_size - 1 and random.random() < 0.05:
                    p1 = replicas[i]
                    p2 = replicas[i + 1]
                    candidates.append(
                        decoder.decode(crossover.uniform_crossover_3d(decoder.encode(p1),
                                                                        decoder.encode(p2)))
                    )
                else:
                    candidates.append(mutator.mutate(replicas[i], temperatures[i]))

            # ─── Parallel candidate evaluation ─────────────────────────────────
            candidate_evaluations = [
                ev for chunk in pool.map(_eval_chunk, split(candidates))
                for ev in chunk
            ]

            # ─── Update dynamic ranges ────────────────────────────────────────
            range_changed = evaluate.update_global(dynamic_min, candidate_evaluations, 'min')
            range_changed = evaluate.update_global(dynamic_max, candidate_evaluations, 'max') or range_changed

            scaled_candidate_evals = [
                evaluate.apply_scale(e, dynamic_min, dynamic_max) for e in candidate_evaluations
            ]
            candidate_scores = [
                evaluate.weighted_sum_scaled(scaled_candidate_evals[i], weight_vectors[i])
                for i in range(paras.population_size)
            ]

            if range_changed:
                scaled_evals = [
                    evaluate.apply_scale(e, dynamic_min, dynamic_max) for e in evaluations
                ]
                scores = [
                    evaluate.weighted_sum_scaled(scaled_evals[i], weight_vectors[i])
                    for i in range(paras.population_size)
                ]
                scaled_elite_evals = [
                    evaluate.apply_scale(e, dynamic_min, dynamic_max) for _, e, _ in elites
                ]
                elites = [
                    (evaluate.weighted_sum_scaled(scaled_elite_evals[i], weight_vectors[0]),
                     elites[i][1], elites[i][2])
                    for i in range(len(elites))
                ]

            range_changed = False

            # ─── Selection ─────────────────────────────────
            replicas, evaluations, scores, elites, jump_accept, better_jumps = \
                selection.selection(temperatures, replicas, evaluations, scores,
                                    candidates, candidate_evaluations, candidate_scores,
                                    elites, num_elites, paras.population_size,
                                    generation_count)

            # ─── Replica swaps ──────────────────────────────────────────────────
            if generation_count % n_swaps == 0:
                replicas, evaluations, scores, swap_accept = \
                    mutation.swap_replicas(temperatures, replicas, evaluations,
                                           scores, generation_count)
                total_swap_accept += swap_accept
                if paras.dev_mode:
                    print(f"SWAP ACCEPTED: {swap_accept}")

            total_jump_accept += jump_accept
            total_better_jumps += better_jumps

            if paras.dev_mode:
                print(f"JUMP ACCEPTED: {jump_accept}")
                print(f"IDEA POINT: {[round(float(v), 2) for v in dynamic_min]}")
            if generation_count % log_range == 0 or paras.dev_mode:
                print(f"BEST SCORE: {round(min(elites, key=lambda e: e[0])[0], 3)}")

    # ─── Final output ─────────────────────────────────────────────────────────
    print('-\t' * 10)
    print("\tFINISHED!")

    evaluator=evaluate.Evaluator(layout)


    if paras.dev_mode:
        for i, replica in enumerate(replicas):
            layout.display(replica, evaluator.evaluate([replica,])[0].items(), name=f'replica_{i}')

    objective_str = "\t".join(objectives)
    print(f"\tSCORE\t{objective_str}")
    for i, elite in enumerate(sorted(elites, key=lambda e: e[0])):
        normalized_score=list(evaluator.evaluate([elite[2],],True)[0].values())
        score_str = "\t\t".join(f"{round(v, 3)}" for v in normalized_score)
        print(f"RANK {i + 1}:\t{round(elite[0], 3)}\t{score_str}")
        if paras.dev_mode:
            binds={"base":{},"shift":{}}
            for idx, kbi in enumerate(elite[2]):
                if kbi is None:
                    continue
                if idx<layout.sizes[0]: layer="base"
                else: layer="shift"
                binds[layer][layout.idx2key[idx]]=layout.keybinds[kbi]
            print(json.dumps(binds,ensure_ascii=False))
        print()
        layout.display(elite[2], zip(objectives, normalized_score), name=f'top_{i + 1}')

    if paras.dev_mode:
        print(f"SWAP ACCEPTANCE RATE:  {total_swap_accept / paras.generation_limit * n_swaps / 2}")
        print(f"JUMP ACCEPTANCE RATE:  {total_jump_accept / (paras.generation_limit - total_better_jumps)}")
        print(f"BETTER JUMPS RATE:  {total_better_jumps / paras.generation_limit}")


if __name__ == '__main__':
    run()