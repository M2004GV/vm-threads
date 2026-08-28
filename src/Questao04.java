public class Questao04 {
    public static void main(String[] args) {
        Thread t1 = new Thread(() -> {
            System.out.println("A");
        });

        Thread t2 = new Thread(() -> {
            System.out.println("B");
        });

        t1.start();
        t2.start();
        System.out.println("C");
    }
}
