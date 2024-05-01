sigint_handler() {
    pkill -P $$
    exit 1
}
trap 'sigint_handler' SIGINT

source ~/miniconda3/etc/profile.d/conda.sh
conda activate auto-code-rover
python main.py & 
cd ./front/ && npm run start