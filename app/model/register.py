from app.model import claude, common, gpt, ollama, groq


def register_all_models() -> None:
    """
    Register all models. This is called in main.
    """
    common.register_model(gpt.Gpt4_Turbo20240409())
    common.register_model(gpt.Gpt4_0125Preview())
    common.register_model(gpt.Gpt4_1106Preview())
    common.register_model(gpt.Gpt35_Turbo0125())
    common.register_model(gpt.Gpt35_Turbo1106())
    common.register_model(gpt.Gpt35_Turbo16k_0613())
    common.register_model(gpt.Gpt35_Turbo0613())
    common.register_model(gpt.Gpt4_0613())

    common.register_model(claude.Claude3Opus())
    common.register_model(claude.Claude3Sonnet())
    common.register_model(claude.Claude3Haiku())

    common.register_model(ollama.Llama3_8B())
    common.register_model(ollama.Llama3_70B())
    
    common.register_model(groq.Llama3_8B())
    common.register_model(groq.Llama3_70B())
    common.register_model(groq.Llama2_70B())
    common.register_model(groq.Mixtral_8x7B())
    common.register_model(groq.Gemma_7B())

    # register default model as selected
    common.SELECTED_MODEL = gpt.Gpt35_Turbo0125()
