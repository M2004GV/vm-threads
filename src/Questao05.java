public class Questao05 {
    public static void main(String[] args) {
        Thread t = new Thread(() -> {
            for (int i = 1; i <= 3; i++) {
                System.out.println(i);
                try {
                    Thread.sleep(1000);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }
        });

        t.start();
    }
}
