class MinhaThread extends Thread {

    @Override
    public void run() {
        System.out.println("Thread em execucao!  [executando em: "
                + Thread.currentThread().getName() + "]");
    }
}

public class Questao01 {

    public static void main(String[] args) throws InterruptedException {

        System.out.println("=== (1) chamando start() -> cria uma nova thread ===");
        MinhaThread t1 = new MinhaThread();
        t1.start();
        t1.join();

        System.out.println();
        System.out.println("=== (2) chamando run() diretamente -> NAO cria thread ===");
        MinhaThread t2 = new MinhaThread();
        t2.run();

        System.out.println();
        System.out.println("Thread principal: " + Thread.currentThread().getName());
    }
}
