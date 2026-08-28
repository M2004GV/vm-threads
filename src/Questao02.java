class Contador implements Runnable {

    @Override
    public void run() {
        for (int i = 1; i <= 10; i++) {
            System.out.println(i);
        }
    }
}

public class Questao02 {

    public static void main(String[] args) {

        Contador tarefa = new Contador();      
        Thread executor = new Thread(tarefa); 

        executor.start();
    }
}


