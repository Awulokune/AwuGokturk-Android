from awa_agent.agent import AwuGokturkAgent

def main():
    agent = AwuGokturkAgent()
    print("AwuGöktürk hazır! Çıkmak için 'exit' yaz.")

    while True:
        try:
            text = input("\nSen: ").strip()
        except EOFError:
            print("\nGirdi kapandı; sohbet sonlandırıldı.")
            break
        except KeyboardInterrupt:
            print("\nSohbet kapatıldı.")
            break

        if text.lower() in {"exit", "quit", "çık"}:
            break
        if not text:
            continue

        try:
            result = agent.handle(text)
            print(f"\nAwuGöktürk [{result.status}]:")
            print(result.message)

            if result.questions:
                print("Sorular:", *result.questions, sep="\n- ")

            if result.code:
                print("\n" + result.code)
        except Exception as exc:
            print(f"Ajan hatası: {exc}")

if __name__ == "__main__":
    main()
