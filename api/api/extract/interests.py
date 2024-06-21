import numpy as np

from api import llm


def __cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# modified from https://arxiv.org/pdf/2305.15498
async def __cluster_messages(
    messages: list[str], epsilon: float, alpha: float, c: int
) -> list[list[int]]:
    message_embeddings = await llm.embed(messages)

    clusters = []
    sum_embeddings = []

    for message_index in range(len(messages)):
        max_similarity = -1
        best_cluster_index = None

        for cluster_index in range(len(clusters)):
            avg_embedding = sum_embeddings[cluster_index] / len(clusters[cluster_index])

            similarity = __cosine_similarity(
                avg_embedding, message_embeddings[message_index]
            )

            if similarity > max_similarity:
                max_similarity = similarity
                best_cluster_index = cluster_index

        if best_cluster_index and max_similarity >= epsilon:
            clusters[best_cluster_index].append(message_index)
            sum_embeddings[best_cluster_index] = np.add(
                sum_embeddings[best_cluster_index], message_embeddings[message_index]
            )
        else:
            clusters.append([message_index])
            sum_embeddings.append(message_embeddings[message_index])

    # try to re-merge clusters that are too small
    for i in range(len(clusters)):
        if len(clusters[i]) >= c:
            continue

        avg_embedding = sum_embeddings[i] / len(clusters[i])

        max_similarity = -1
        best_cluster_index = None

        for j in range(i + 1, len(clusters)):
            avg_embedding2 = sum_embeddings[j] / len(clusters[j])

            similarity = __cosine_similarity(avg_embedding, avg_embedding2)

            if similarity > max_similarity:
                max_similarity = similarity
                best_cluster_index = j

        if best_cluster_index and max_similarity >= alpha:
            clusters[best_cluster_index].extend(clusters[i])
            sum_embeddings[best_cluster_index] = np.add(
                sum_embeddings[best_cluster_index], sum_embeddings[i]
            )
            clusters[i] = []

    # remove clusters that are still too small
    clusters = [cluster for cluster in clusters if len(cluster) >= c]

    return clusters


async def __get_cluster_topics(clusters: list[list[str]]) -> list[list[str]]:
    topics = []

    for cluster in clusters:
        system_prompt = (
            "Your task is to identify the primary topic of conversation based on a"
            "list of chatbot questions. Identify this topic as a single noun phrase "
            "that captures the main topics of interest present in the majority of "
            "responses, focusing on subjects, locations, or objects mentioned. If no "
            "clear topic is identifiable, return 'n/a'."
        )
        prompt_data = "\n".join(cluster)
        response = await llm.generate(
            model=llm.MODEL_GPT_4,
            system=system_prompt,
            prompt=prompt_data,
        )

        print(response)

        if response != "n/a":
            topics.append(response.strip())

    return topics


async def __get_interests_from_topics(topics: list[str]) -> list[str]:
    system_prompt = (
        "As an interest analyst, your task is to generate a coherent list of interests "
        "based on a given list of conversation topics. Each interest should be a "
        "single noun phrase, focusing specifically on subjects, locations, or objects. "
        "Do not repeat interests."
    )
    prompt_data = "\n".join(topics)
    response = await llm.generate(
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return response.strip().split("\n")


async def extract_interests(messages) -> list[str]:
    responses = [response for _, response in messages]

    clustered_messages_indices = await __cluster_messages(
        responses, epsilon=0.7, alpha=0.3, c=len(messages) // 25
    )

    clustered_prompts = [
        [messages[i][0] for i in cluster] for cluster in clustered_messages_indices
    ]

    topics = await __get_cluster_topics(clustered_prompts)
    interests = await __get_interests_from_topics(topics)

    return interests
